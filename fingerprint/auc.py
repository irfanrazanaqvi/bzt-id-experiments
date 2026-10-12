import sys, pandas as pd
from sklearn.metrics import roc_auc_score
d = pd.read_csv(sys.argv[1]); c = d[d.split == "calibration"]   # choose the setting on the calibration split only
print(sys.argv[2], "calibration_AUC", round(roc_auc_score(c.genuine, c.cosine), 4))
