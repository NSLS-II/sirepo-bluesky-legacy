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

from ophyd.utils import make_dir_tree

from srw_handler import SRWFileHandler
import matplotlib.pyplot as plt


RE = RunEngine({})

bec = best_effort.BestEffortCallback()
RE.subscribe(bec)

# MongoDB backend:
# db = Broker.named('local')  # mongodb backend
# try:
#     databroker.assets.utils.install_sentinels(db.reg.config, version=1)
# except:
#     pass

# Temp sqlite backend:
db = Broker.from_config(temp_config())

RE.subscribe(db.insert)
db.reg.register_handler('srw', SRWFileHandler, overwrite=True)

plt.ion()
install_qt_kicker()

_ = make_dir_tree(2018, base_path='/tmp/data')
