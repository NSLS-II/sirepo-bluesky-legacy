import datetime
from pathlib import Path

import unyt as u

from bluesky.tests.utils import _print_redirect
from ophyd import Device, Signal, Component as Cpt
from ophyd.sim import SynAxis, NullStatus, new_uid

from srw_handler import read_srw_file
from sirepo_bluesky import SirepoBluesky


class SirepoDetector(Device):
    """
    Use SRW code based on the value of the motor.

    Parameters
    ----------
    name : str
        The name of the detector
    sirepo_component : str
       Ophyd object corresponsing to Sirepo component with parameters being
       changed
    field0 : str
        The name of the first parameter of the component being changed
    field0_units : str
        The Sirepo units for field0 that must be converted to before scan
    field1 : str
        The name of the second parameter of the component being changed
    field1_units : str
        The Sirepo units for field1 that must be converted to before scan
    reg : Databroker registry
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

    def __init__(self, name, sirepo_component=None, field0=None, field0_units=None, field1=None,
                 field1_units=None, reg=None, sim_id=None, watch_name=None, sirepo_server='http://10.10.10.10:8000',
                 **kwargs):
        super().__init__(name=name, **kwargs)
        self.reg = reg
        self.sirepo_component = sirepo_component
        self.field0 = field0
        self.field0_units = field0_units
        self.field1 = field1
        self.field1_units = field1_units
        self._resource_id = None
        self._result = {}
        self._sim_id = sim_id
        self.watch_name = watch_name
        self.sb = None
        self.data = None
        self._hints = None
        self.sirepo_server = sirepo_server
        assert sim_id, 'Simulation ID must be provided. Currently it is set to {}'.format(sim_id)
        self.connect(sim_id=self._sim_id)

    @property
    def hints(self):
        if self._hints is None:
            return {'fields': [self.mean.name]}
        return self._hints

    @hints.setter
    def hints(self, val):
        self._hints = dict(val)

    def update_value(self, value, units):
        unyt_obj = u.m
        starting_unit = value * unyt_obj
        converted_unit = starting_unit.to(units)
        return converted_unit

    def trigger(self):
        super().trigger()
        if self.field1 is not None:
            x = getattr(self.sirepo_component, self.field0).read()[f'{self.sirepo_component.name}_{self.field0}']['value']
        if self.field1 is not None:
            y = getattr(self.sirepo_component, self.field1).read()[f'{self.sirepo_component.name}_{self.field1}']['value']
        datum_id = new_uid()
        date = datetime.datetime.now()
        srw_file = Path('/tmp/data') / Path(date.strftime('%Y/%m/%d')) / \
            Path('{}.dat'.format(datum_id))

        element = self.sb.find_element(self.data['models']['beamline'], 'title', self.sirepo_component.name)
        print(element)
        if self.field0 is not None:
            real_field0 = self.field0.replace('sirepo_','')
        if self.field1 is not None:
            real_field1 = self.field1.replace('sirepo_', '')

        if self.field0 is not None:
            element[real_field0] = float(self.update_value(x, self.field0_units).value)

        if self.field1 is not None:
            element[real_field1] = float(self.update_value(y, self.field1_units).value)

        watch = self.sb.find_element(self.data['models']['beamline'], 'title', self.watch_name)
        self.data['report'] = 'watchpointReport{}'.format(watch['id'])
        self.sb.run_simulation()
        
        with open(srw_file, 'wb') as f:
            f.write(self.sb.get_datafile())
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

    def find_optic_id_by_name(self, optic_name, data):
        for i in range(len(data['models']['beamline'])):
            if data['models']['beamline'][i]['title'] == optic_name:
                return i
        raise ValueError(f'Not valid optic {optic_name}')

    def connect(self, sim_id):
        sb = SirepoBluesky(self.sirepo_server)
        data, sirepo_schema = sb.auth('srw', sim_id)
        self.data = data
        self.sb = sb

        watchpoints = {}
        print("Tunable parameters for Bluesky scan: ")

        for i in range(len(data['models']['beamline'])):
            print('OPTICAL ELEMENT:    ' + data['models']['beamline'][i][
                'title'])
            parameters = []
            for key in data['models']['beamline'][i]:
                parameters.append(key)
            print(f'PARAMETERS:        {parameters} \n')
            if data['models']['beamline'][i]['type'] == 'watch':
                watchpoints[data['models']['beamline'][i]['title']] = \
                    str(data['models']['beamline'][i]['position'])
        print(f'WATCHPOINTS:       {watchpoints}')
        if len(watchpoints) < 1:
            raise ValueError(
                'No watchpoints found. This simulation will not work')

        optic_name = input("Please select optical element: ")
        watch_name = input("Please select watchpoint: ")

        field0 = input("Please select parameter: ")
        if optic_name != watch_name:
            if field0 is not '':
                field0_units = \
                sb.schema['model'][optic_name.lower()][field0][0].split('[')[
                    1].split(']')[0]
                field0 = f'sirepo_{field0}'
        else:
            if field0 is not '':
                field0_units = \
                sb.schema['model']['watch'][field0][0].split('[')[1].split(']')[0]
                field0 = f'sirepo_{field0}'

        field1 = input(
            "Please select another parameter or press ENTER to only use one: ")
        field1_units = None
        if field1 is not '':
            field1_units = \
            sb.schema['model'][optic_name.lower()][field1][0].split('[')[
                1].split(']')[0]
            field1 = f'sirepo_{field1}'
        else:
            field1 = None

        # First define a factory
        optic_id = self.find_optic_id_by_name(optic_name, data)
        schema = {f'sirepo_{k}': v for k, v in
                  data['models']['beamline'][optic_id].items()}

        def class_factory(cls_name):
            dd = {k: Cpt(SynAxis) for k in schema}
            return type(cls_name, (Device,), dd)

        SirepoComponent = class_factory('SirepoComponent')
        sirepo_component = SirepoComponent(name=optic_name)

        self.sirepo_component = sirepo_component

        if field0 is not '':
            self.field0 = field0
            self.field0_units = field0_units
        if field1 is not '':
            self.field1 = field1
            self.field1_units = field1_units
        self.watch_name = watch_name

    def get_sirepo_component(self):
        return self.sirepo_component

    def get_field0(self):
        return self.field0

    def get_field1(self):
        return self.field1


if __name__ == "__main__":

    sim_id = input("Please enter sim ID: ")
    sirepo_det = SirepoDetector(name='sirepo_det', sim_id=sim_id, reg=db.reg)

    sirepo_component = sirepo_det.get_sirepo_component()
    field0 = sirepo_det.get_field0()
    field1 = sirepo_det.get_field1()

    sirepo_det.read_attrs = ['image', 'mean', 'photon_energy']
    sirepo_det.configuration_attrs = ['horizontal_extent', 'vertical_extent',
                                   'shape']

    # Grid scan
    #RE(bp.grid_scan([sirepo_det],
                    #getattr(sirepo_component, field0), 0, 1e-3, 10,
                    #getattr(sirepo_component, field1), 0, 1e-3, 10,
                    #True))
    # 1D scan
    #RE(bps.mov(getattr(sirepo_component, field1), 1e-3))
    #RE(bp.scan([sirepo_det], getattr(sirepo_component, field0), 0, 1e-3, 10))

    # Watchpoint scan
    #RE(bp.rel_scan([sirepo_det], getattr(sirepo_component, field0), -.1, .1, 11))

