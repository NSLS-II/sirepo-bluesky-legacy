import datetime
from pathlib import Path

from bluesky.tests.utils import _print_redirect

from ophyd import Device, Signal, Component as Cpt
from ophyd.sim import SynAxis, NullStatus, new_uid

from srw_handler import read_srw_file
from sirepo_bluesky import SirepoBluesky

class SRWDetector(Device):
    """
    Use SRW code based on the value of the motor.

    Parameters
    ----------
    name : str
        The name of the detector
    optic_name : str
        The name of the optic being accessed by Bluesky
    param0 : str
        The name of the first parameter of the optic being changed
    motor0 : Ophyd Component
        The first Ophyd component being controlled in Bluesky scan
    field0 : str
        The name corresponding to motor0 that is shown as axis in Bluesky scan
    param1 : str
        The name of the second parameter of the optic being changed
    motor1 :
        The second Ophyd component being controlled in Bluesky scan
    field1 : str
        The name corresponding to motor1 that is shown as axis in Bluesky scan
    reg : Databroker register
    sim_id : str
        The simulation id corresponding to the Sirepo simulation being run on
        local server
    watch_name : str
        The name of the watchpoint viewing the simulation
    sirepo_server : str
        Address that identifies access to local Sirepo server

    """
    image = Cpt(Signal)
    shape = Cpt(Signal)
    mean = Cpt(Signal)
    photon_energy = Cpt(Signal)
    horizontal_extent = Cpt(Signal)
    vertical_extent = Cpt(Signal)

    def __init__(self, name, sirepo_component, field0, field1=None, reg=None,
                 sim_id=None, watch_name=None, sirepo_server='http://10.10.10.10:8000',
                 **kwargs):
        super().__init__(name=name, **kwargs)
        self.reg = reg
        self.sirepo_component = sirepo_component
        self.field0 = field0
        self.field1 = field1
        self._resource_id = None
        self._result = {}
        self._sim_id = sim_id
        self.watch_name = watch_name
        self._sirepo_server = sirepo_server
        self._hints = None
        assert sim_id, 'Simulation ID must be provided. Currently it is set to {}'.format(sim_id)

    @property
    def hints(self):
        if self._hints is None:
            return {'fields': [self.mean.name]}
        return self._hints

    @hints.setter
    def hints(self, val):
        self._hints = dict(val)

    def trigger(self):
        super().trigger()
        x = getattr(self.sirepo_component, self.field0).read()[f'{self.sirepo_component.name}_{self.field0}']['value']
        y = getattr(self.sirepo_component, self.field1).read()[f'{self.sirepo_component.name}_{self.field1}']['value']
        datum_id = new_uid()
        date = datetime.datetime.now()
        srw_file = Path('/tmp/data') / Path(date.strftime('%Y/%m/%d')) / \
            Path('{}.dat'.format(datum_id))

        sim_id = self._sim_id
        sb = SirepoBluesky(self._sirepo_server)
        data = sb.auth('srw', sim_id)

        # Get units we need to convert to
        sb_data = sb.get_datafile()
        # start = sb_data.find('[')
        # end = sb_data.find(']')
        # final_units = sb_data[start + 1:end]

        element = sb.find_element(data['models']['beamline'], 'title', self.sirepo_component.name)
        element[self.field0] = x * 1000
        element[self.field1] = y * 1000
        watch = sb.find_element(data['models']['beamline'], 'title', self.watch_name)
        data['report'] = 'watchpointReport{}'.format(watch['id'])
        sb.run_simulation()
        
        with open(srw_file, 'wb') as f:
            f.write(sb.get_datafile())
        ret = read_srw_file(srw_file)
        self.image.put(datum_id)
        self.shape.put(ret['shape'])
        self.mean.put(ret['mean'])
        self.photon_energy.put(ret['photon_energy'])
        self.horizontal_extent.put(ret['horizontal_extent'])
        self.vertical_extent.put(ret['vertical_extent'])

        self._resource_id = self.reg.insert_resource('srw', srw_file, {})
        self.reg.insert_datum(self._resource_id, datum_id, {})

        return NullStatus()

    def describe(self):
        res = super().describe()
        res[self.image.name].update(dict(external="FILESTORE"))
        return res

    def unstage(self):
        super().unstage()
        self._resource_id = None
        self._result.clear()


class Positioner(Device):
    x = Cpt(SynAxis)
    y = Cpt(SynAxis)


if __name__ == "__main__":
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

    sim_id = input("Please enter sim ID: ")

    sb = SirepoBluesky('http://10.10.10.10:8000')
    data = sb.auth('srw', sim_id)
    watchpoints = {}
    print("Tunable parameters for Bluesky scan: ")

    non_parameters = ('title', 'type', 'id')

    for i in range(len(data['models']['beamline'])):
        print('OPTICAL ELEMENT:    ' + data['models']['beamline'][i]['title'])
        parameters = []
        for key in data['models']['beamline'][i]:
            if key not in non_parameters:
                parameters.append(key)
        print(f'PARAMETERS:        {parameters} \n')
        if data['models']['beamline'][i]['type'] == 'watch':
            watchpoints[data['models']['beamline'][i]['title']] = \
                str(data['models']['beamline'][i]['position'])
    print(f'WATCHPOINTS:       {watchpoints}')
    if len(watchpoints) < 1:
        raise ValueError('No watchpoints found. This simulation will not work')

    optic_name = input("Please select optical element: ")

    def find_optic_id_by_name(optic_name):
        for i in range(len(data['models']['beamline'])):
            if data['models']['beamline'][i]['title'] == optic_name:
                return i
        raise ValueError(f'Not valid optic {optic_name}')

    field0 = input("Please select parameter: ")
    field1 = input("Please select another parameter or press ENTER to only use one: ")
    watch_name = input("Please select watchpoint: ")

    # First define a factory
    optic_id = find_optic_id_by_name(optic_name)
    schema = {f'sirepo_{k}': v for k, v in data['models']['beamline'][optic_id].items()}
              #if k not in non_parameters}
    def class_factory(cls_name):
        dd = {k: Cpt(SynAxis) for k in schema}
        return type(cls_name, (Device,), dd)

    SirepoComponent = class_factory('SirepoComponent')
    sirepo_component = SirepoComponent(name=optic_name)

    srw_det = SRWDetector(name='srw_det', sirepo_component=sirepo_component,
                          field0=f'sirepo_{field0}',
                          field1=f'sirepo_{field1}',
                          reg=db.reg, sim_id=sim_id, watch_name=watch_name)
    srw_det.read_attrs = ['image', 'mean', 'photon_energy']
    srw_det.configuration_attrs = ['horizontal_extent', 'vertical_extent',
                                   'shape']

    RE(bp.grid_scan([srw_det],
                    getattr(sirepo_component, f'sirepo_{field0}'), 0, 1e-3, 10,
                    getattr(sirepo_component, f'sirepo_{field1}'), 0, 1e-3, 10,
                    True))





