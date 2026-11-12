# Machine Learning

## Chapter 1 — The ML workflow
Define the problem, collect and clean data, split into train, validation and test sets, train a baseline, iterate, evaluate once on the test set. Data leakage happens when information from the test set influences training.

## Chapter 2 — Classification metrics
Accuracy is misleading on imbalanced data. Precision = TP / (TP + FP), recall = TP / (TP + FN), F1 is their harmonic mean. The ROC curve plots the true positive rate against the false positive rate; AUC summarises it.

## Chapter 3 — Tree-based models
Decision trees split the data on the feature that best reduces impurity. Random forests average many trees trained on bootstrap samples. Gradient boosting adds trees sequentially, each one correcting the errors of the previous ones.

## Chapter 4 — Overfitting and regularisation
A model overfits when it learns noise: low training error, high validation error. Remedies: more data, simpler models, cross-validation, L1/L2 regularisation, early stopping.

## Chapter 5 — Model deployment
Serialise the model, expose it behind an API, version it, monitor data drift and performance in production.
