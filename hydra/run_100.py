"""Fast 100-iteration run with reduced model complexity for small dataset."""
import sys
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/Martin/Dominion")

import hydra.models.gbm as gbm
import hydra.models.forests as forests
import hydra.models.neural as neural

gbm.LGBM_PARAMS["n_estimators"] = 200
gbm.XGB_PARAMS["n_estimators"] = 200
gbm.CAT_PARAMS["iterations"] = 200
forests.RF_PARAMS["n_estimators"] = 200
forests.ET_PARAMS["n_estimators"] = 200
forests.HGB_PARAMS["max_iter"] = 200
neural.MLP_PARAMS["max_iter"] = 50
neural.LSTM_PARAMS["epochs"] = 5
neural.TCN_PARAMS["epochs"] = 5

from hydra.models.stacking import StackingEnsemble
StackingEnsemble.__init__.__defaults__ = (3,)  # 3 inner folds instead of 5

from hydra.loop.improver import HydraImprover

imp = HydraImprover(brain="all", no_loop=False)
result = imp.run()

print("\n=== FINAL RESULT ===")
import json
print(json.dumps(
    {k: round(v, 4) if isinstance(v, float) else v for k, v in result.items()},
    indent=2
))
