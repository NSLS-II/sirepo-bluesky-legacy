import bluesky.preprocessors as bpp
import bluesky.plan_stubs as bps
import bluesky.plans as bp
from bluesky.run_engine import RunEngine
from bluesky.callbacks import best_effort
from bluesky.simulators import summarize_plan
from bluesky.utils import install_qt_kicker
from bluesky.utils import ProgressBarManager

import databroker
from databroker import Broker, temp_config

from srw_handler import SRWFileHandler
import matplotlib.pyplot as plt

RE = RunEngine({})

bec = best_effort.BestEffortCallback()
RE.subscribe(bec)

db = Broker.named('local')
RE.subscribe(db.insert)
db.reg.register_handler('srw', SRWFileHandler, overwrite=True)
try:
    databroker.assets.utils.install_sentinels(db.reg.config, version=1)
except:
    pass

plt.ion()
install_qt_kicker()

