"""align studyplan contract

Aligne le schéma sur le contrat d'API officiel (STUDYPLAN_SPEC.md) :
- échéances : weight 0-100 et date simple, type exam ou assignment ; une
  échéance porte sur toute sa matière (deadline_chapters supprimée) ;
- disponibilités : créneaux hebdomadaires seuls (exceptions supprimées) ;
- profil : session_minutes, durée de chaque session du planning ;
- plannings : une semaine ISO par planning, un planning actif par semaine.

Écrite à la main à partir de --autogenerate, qui produisait une migration
fausse : colonnes NOT NULL ajoutées sans reprise des lignes existantes (échec
sur toute base non vide), contraintes CHECK nouvelles absentes, anciennes
contraintes CHECK laissées sur des colonnes supprimées.

Revision ID: b446582e501b
Revises: 9be33fb072bc
Create Date: 2026-11-12 13:11:36.284026+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import backend.db.types


# revision identifiers, used by Alembic.
revision: str = 'b446582e501b'
down_revision: Union[str, Sequence[str], None] = '9be33fb072bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEADLINE_TYPE = sa.Enum(
    "exam", "assignment", name="type_values", native_enum=False, create_constraint=True
)
OLD_DEADLINE_TYPE = sa.Enum(
    "exam", "project", name="type_values", native_enum=False, create_constraint=True
)


def upgrade() -> None:
    """Applique la migration."""
    # --- Tables abandonnées par le contrat -----------------------------------
    with op.batch_alter_table("availability_exceptions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_availability_exceptions_user_id"))
    op.drop_table("availability_exceptions")

    with op.batch_alter_table("deadline_chapters", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_deadline_chapters_chapter_id"))
    op.drop_table("deadline_chapters")

    # --- Disponibilités : créneaux hebdomadaires seuls -----------------------
    with op.batch_alter_table("availabilities", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("ck_availabilities_valid_range"), type_="check")
        batch_op.drop_column("valid_to")
        batch_op.drop_column("valid_from")

    # --- Échéances : weight et date simple -----------------------------------
    with op.batch_alter_table("deadlines", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("ck_deadlines_importance_range"), type_="check")
        batch_op.drop_constraint(batch_op.f("ck_deadlines_type_values"), type_="check")
        batch_op.add_column(sa.Column("due_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("weight", sa.Integer(), nullable=True))

    # Reprise des lignes existantes : date locale du jour de l'échéance, poids
    # déduit de l'importance, « project » devient « assignment ».
    op.execute(
        "UPDATE deadlines SET due_date = substr(due_at, 1, 10), "
        "weight = CASE importance WHEN 1 THEN 30 WHEN 3 THEN 70 ELSE 50 END, "
        "type = CASE type WHEN 'project' THEN 'assignment' ELSE type END"
    )

    with op.batch_alter_table("deadlines", schema=None) as batch_op:
        batch_op.alter_column("due_date", existing_type=sa.Date(), nullable=False)
        batch_op.alter_column("weight", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column(
            "type", existing_type=sa.VARCHAR(length=7), type_=DEADLINE_TYPE, existing_nullable=False
        )
        batch_op.drop_column("due_at")
        batch_op.drop_column("importance")
        batch_op.create_check_constraint(
            batch_op.f("ck_deadlines_weight_range"), "weight BETWEEN 0 AND 100"
        )

    # --- Profil : durée des sessions -----------------------------------------
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("ck_user_settings_max_session_range"), type_="check")
        batch_op.add_column(sa.Column("session_minutes", sa.Integer(), nullable=True))

    op.execute("UPDATE user_settings SET session_minutes = max_session_min")

    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.alter_column("session_minutes", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column("max_session_min")
        batch_op.create_check_constraint(
            batch_op.f("ck_user_settings_session_minutes_range"),
            "session_minutes BETWEEN 15 AND 240",
        )

    # --- Plannings : une semaine ISO par planning ----------------------------
    with op.batch_alter_table("plans", schema=None) as batch_op:
        batch_op.add_column(sa.Column("week", sa.String(length=8), nullable=True))

    # Aucun planning n'existe encore (le générateur n'est pas écrit) ; au cas où,
    # semaine approchée depuis la date de création.
    op.execute("UPDATE plans SET week = strftime('%Y-W%W', created_at)")

    with op.batch_alter_table("plans", schema=None) as batch_op:
        batch_op.alter_column("week", existing_type=sa.String(length=8), nullable=False)
        batch_op.drop_index(
            batch_op.f("uq_plans_user_id_active"), sqlite_where=sa.text("status = 'active'")
        )
        batch_op.create_index(batch_op.f("ix_plans_week"), ["week"], unique=False)
        batch_op.create_index(
            "uq_plans_user_id_week_active",
            ["user_id", "week"],
            unique=True,
            sqlite_where=sa.text("status = 'active'"),
        )
        batch_op.create_check_constraint(
            batch_op.f("ck_plans_week_format"), "week GLOB '[0-9][0-9][0-9][0-9]-W[0-9][0-9]'"
        )


def downgrade() -> None:
    """Annule la migration (les exceptions et liens échéance-chapitre sont perdus)."""
    # --- Plannings -----------------------------------------------------------
    with op.batch_alter_table("plans", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("ck_plans_week_format"), type_="check")
        batch_op.drop_index(
            "uq_plans_user_id_week_active", sqlite_where=sa.text("status = 'active'")
        )
        batch_op.drop_index(batch_op.f("ix_plans_week"))
        batch_op.create_index(
            batch_op.f("uq_plans_user_id_active"),
            ["user_id"],
            unique=True,
            sqlite_where=sa.text("status = 'active'"),
        )
        batch_op.drop_column("week")

    # --- Profil --------------------------------------------------------------
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.drop_constraint(
            batch_op.f("ck_user_settings_session_minutes_range"), type_="check"
        )
        batch_op.add_column(sa.Column("max_session_min", sa.Integer(), nullable=True))

    op.execute("UPDATE user_settings SET max_session_min = session_minutes")

    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.alter_column("max_session_min", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column("session_minutes")
        batch_op.create_check_constraint(
            batch_op.f("ck_user_settings_max_session_range"), "max_session_min BETWEEN 15 AND 240"
        )

    # --- Échéances -----------------------------------------------------------
    with op.batch_alter_table("deadlines", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("ck_deadlines_weight_range"), type_="check")
        batch_op.drop_constraint(batch_op.f("ck_deadlines_type_values"), type_="check")
        batch_op.add_column(sa.Column("due_at", sa.VARCHAR(length=20), nullable=True))
        batch_op.add_column(sa.Column("importance", sa.Integer(), nullable=True))

    op.execute(
        "UPDATE deadlines SET due_at = due_date || 'T00:00:00Z', "
        "importance = CASE WHEN weight < 40 THEN 1 WHEN weight > 60 THEN 3 ELSE 2 END, "
        "type = CASE type WHEN 'assignment' THEN 'project' ELSE type END"
    )

    with op.batch_alter_table("deadlines", schema=None) as batch_op:
        batch_op.alter_column("due_at", existing_type=sa.VARCHAR(length=20), nullable=False)
        batch_op.alter_column("importance", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column(
            "type",
            existing_type=sa.VARCHAR(length=10),
            type_=OLD_DEADLINE_TYPE,
            existing_nullable=False,
        )
        batch_op.drop_column("weight")
        batch_op.drop_column("due_date")
        batch_op.create_check_constraint(
            batch_op.f("ck_deadlines_importance_range"), "importance BETWEEN 1 AND 3"
        )

    # --- Disponibilités ------------------------------------------------------
    with op.batch_alter_table("availabilities", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("valid_from", sa.Date(), nullable=False, server_default="2026-01-01")
        )
        batch_op.add_column(sa.Column("valid_to", sa.Date(), nullable=True))
        batch_op.create_check_constraint(
            batch_op.f("ck_availabilities_valid_range"),
            "valid_to IS NULL OR valid_to >= valid_from",
        )

    # --- Tables abandonnées --------------------------------------------------
    op.create_table(
        "deadline_chapters",
        sa.Column("deadline_id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            name=op.f("fk_deadline_chapters_chapter_id_chapters"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deadline_id"],
            ["deadlines.id"],
            name=op.f("fk_deadline_chapters_deadline_id_deadlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("deadline_id", "chapter_id", name=op.f("pk_deadline_chapters")),
    )
    with op.batch_alter_table("deadline_chapters", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_deadline_chapters_chapter_id"), ["chapter_id"], unique=False
        )

    op.create_table(
        "availability_exceptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("starts_local", backend.db.types.LocalTime(length=5), nullable=True),
        sa.Column("ends_local", backend.db.types.LocalTime(length=5), nullable=True),
        sa.Column(
            "kind",
            sa.Enum("blocked", "added", name="kind_values", native_enum=False, create_constraint=True),
            nullable=False,
        ),
        sa.Column("created_at", backend.db.types.UtcDateTime(length=20), nullable=False),
        sa.Column("updated_at", backend.db.types.UtcDateTime(length=20), nullable=False),
        sa.CheckConstraint(
            "starts_local IS NOT NULL OR kind = 'blocked'",
            name=op.f("ck_availability_exceptions_whole_day_blocked"),
        ),
        sa.CheckConstraint(
            "(starts_local IS NULL) = (ends_local IS NULL)",
            name=op.f("ck_availability_exceptions_times_both_or_none"),
        ),
        sa.CheckConstraint(
            "starts_local IS NULL OR ends_local > starts_local",
            name=op.f("ck_availability_exceptions_ends_after_starts"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_availability_exceptions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_availability_exceptions")),
    )
    with op.batch_alter_table("availability_exceptions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_availability_exceptions_user_id"), ["user_id"], unique=False
        )
