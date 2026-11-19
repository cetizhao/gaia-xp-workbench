"""逐次光谱展示的观测组、时间、来源和掩码约束。"""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from gaia_accretion.classical.xp_workbench import digest
from gaia_accretion.epoch_report import epoch_section, epoch_summary, load_epoch_bundle


SID = '6719035052475592576'


def spectrum():
    return dict(wave=np.array([400., 401., 402.]), flux=np.array([1., 2., 3.])*1e-15,
                mask=np.array([True, False, True]))


def archive():
    products = []
    for i, (arm, role) in enumerate([('UVB', 'wide'), ('VIS', 'wide'), ('UVB', 'narrow'), ('VIS', 'narrow')]):
        products.append(dict(product_id=str(i), obs_id='single-observation', instrument='XSHOOTER',
                             arm=arm, role=role, obs_time=f'2022-05-06T08:41:3{i}.123', time_scale='UTC',
                             arrays=dict(wave_nm=np.array([400., 401., 402.]),
                                         flux_w_m2_nm=np.array([1., 2., 3.])*1e-15,
                                         mask=np.array([True, False, True]))))
    return dict(source_id=SID, products=products)


def bundle(folder):
    np.savez(folder/'one.npz', source_id=np.array(SID), wave_nm=[400., 401., 402.],
             flux_w_m2_nm=[1e-15, 2e-15, 3e-15], mask=np.ones(3, dtype=bool))
    data = dict(schema_version=1, source_id=SID, wavelength_unit='nm', flux_unit='W m-2 nm-1',
                records=[dict(epoch_id='one', group_id='visit-one', instrument='Test instrument',
                              calibration_reference='Synthetic test fixture only', arrays_file='one.npz',
                              sha256=digest(folder/'one.npz'),
                              time=dict(value='59000.123456789', format='MJD', scale='TCB', definition='midpoint'))])
    (folder/'epochs.json').write_text(json.dumps(data), encoding='utf-8')
    return data


class EpochReportTests(unittest.TestCase):
    def test_arms_and_slits_are_one_group_not_four_epochs(self):
        data = archive()
        summary = epoch_summary(spectrum(), data)
        self.assertEqual(summary['observation_groups'], 1)
        self.assertEqual(summary['spectral_products'], 4)
        self.assertEqual(summary['gaia_dr4_records'], 0)
        second = dict(data['products'][0], obs_id='second-observation', product_id='second')
        data['products'].append(second)
        self.assertEqual(epoch_summary(spectrum(), data)['observation_groups'], 2)

    def test_mean_reference_is_not_an_epoch(self):
        result = epoch_summary(spectrum())
        self.assertEqual(result['observation_groups'], 0)
        self.assertEqual(result['spectral_products'], 0)
        self.assertTrue(result['gaia_dr3_mean_is_reference'])

    def test_mask_gaps_and_native_arrays_survive_html(self):
        html = epoch_section(spectrum(), archive())
        payload = html.split('<script type="application/json" id="epoch-data">')[1].split('</script>')[0]
        data = json.loads(payload)
        self.assertEqual(data['series'][0]['y'], [1., None, 3.])
        self.assertEqual(len(data['series']), 5)
        self.assertEqual(sum(row['default'] for row in data['series']), 3)
        self.assertEqual(data['series'][1]['x'], [400., 401., 402.])

    def test_metadata_cannot_break_out_of_json_script(self):
        data = archive()
        malicious = '</script><script>alert(1)</script>'
        data['products'][0]['instrument'] = malicious
        html = epoch_section(spectrum(), data)
        self.assertNotIn(malicious, html)
        payload = html.split('<script type="application/json" id="epoch-data">')[1].split('</script>')[0]
        self.assertEqual(json.loads(payload)['series'][1]['instrument'], malicious)

    def test_bundle_keeps_time_scale_and_checks_all_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            bundle(folder)
            data = load_epoch_bundle(folder, SID)
            self.assertEqual(data['records'][0]['time']['scale'], 'TCB')
            self.assertEqual(data['records'][0]['time']['value'], '59000.123456789')
            self.assertEqual(len(data['input_files']), 2)
            with self.assertRaises(ValueError):
                load_epoch_bundle(folder, '6719035052475592577')
            (folder/'one.npz').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                load_epoch_bundle(folder, SID)

    def test_missing_or_invalid_time_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            data = bundle(folder)
            for time in [dict(value='NaN', format='MJD', scale='UTC', definition='start'),
                         dict(value='59000', format='MJD', scale='', definition='start'),
                         dict(value='100', format='offset days', scale='TCB', definition='midpoint')]:
                data['records'][0]['time'] = time
                (folder/'epochs.json').write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_epoch_bundle(folder, SID)

    def test_dr4_preserves_native_identity_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            data = bundle(folder)
            row = data['records'][0]
            row['release'] = 'Gaia DR4'
            (folder/'epochs.json').write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaises(ValueError):
                load_epoch_bundle(folder, SID)
            row.update(native_source_id='6719035052475592577', identity_reference='Synthetic crossmatch fixture only')
            (folder/'epochs.json').write_text(json.dumps(data), encoding='utf-8')
            result = load_epoch_bundle(folder, SID)
            self.assertEqual(result['source_id'], SID)
            self.assertEqual(result['records'][0]['native_source_id'], row['native_source_id'])
