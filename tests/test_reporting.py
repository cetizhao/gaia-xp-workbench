"""报告必须只读取保存结果，保留零分支并生成可脱离源目录打开的HTML。"""
import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from gaia_accretion import reporting
from gaia_accretion.classical import xp_workbench as work


def saved_run(folder):
    folder.mkdir()
    sid = '6719035052475592576'
    meta = dict(source_id=sid, release='Gaia DR3', product='mean_xp', spt_num=66., av_mag=2., teff_k=4300.,
                calibration_version='test fixture', input_reference='synthetic', prior_reference='synthetic')
    contract = dict(metadata=meta, config=dict(rv=3.1, degrees_of_freedom=4.,fit_windows_nm=[[340+i*30,360+i*30] for i in range(16)]))
    work.write_json(folder/'run_contract.json', contract)
    np.savez(folder/'spectrum.npz',source_id=np.array(sid),wave=np.arange(336.,1021.,2.),flux=np.ones(343),mask=np.ones(343,bool),noise_factor=np.ones((343,2))*.1)
    np.savez(folder/'prediction.npz',lower=np.ones(343)*.9,median=np.ones(343),upper=np.ones(343)*1.1,photo=np.ones(343)*.8,slab=np.ones(343)*.2,
             band_observed=np.ones(16),band_predicted=np.ones(16),band_error=np.ones(16)*.1,band_residual_sigma=np.zeros(16))
    np.savez(folder/'posterior.npz',positive_spt=np.linspace(65,67,20),positive_av_mag=np.linspace(1,2,20),positive_r_red=np.linspace(.01,.2,20),positive_facc_w_m2=np.linspace(1e-14,1e-13,20))
    summary=dict(source_id=sid,posterior_sha256=work.digest(folder/'posterior.npz'),run_contract_sha256=work.digest(folder/'run_contract.json'))
    report=dict(source_id=sid,name='<script>alert(1)</script>',metadata=meta,quantities={'facc_w_m2':[0.,0.,0.,0.]},quantile_levels=[.16,.5,.84,.95],
                numerical_status='passed',p_zero=1.,ln_bayes_factor=-9.,method_id='test_fixture',diagnostic_metrics={'p_spt_edge':None},
                diagnostic_flags=[],stellar_conversion='未提供距离',prior_note='未检查先验敏感性',limits=['仅测试'])
    work.write_json(folder/'summary.json',summary);work.write_json(folder/'review.json',report)
    work.write_json(folder/'status.json',dict(status='complete',source_id=sid,artifact_hashes={n:work.digest(folder/n) for n in ['summary.json','review.json']}))


def fake_plots(destination, *args):
    png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a/9sAAAAASUVORK5CYII=')
    names={k:k+'.png' for k in ['overview','spectrum','posterior']}
    for name in names.values():(destination/name).write_bytes(png)
    return names


class ReportTests(unittest.TestCase):
    def test_offline_zero_branch_readonly_without_backend(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);run=base/'run';saved_run(run)
            before={p.name:work.digest(p) for p in run.iterdir()}
            with patch.object(work,'fit',side_effect=AssertionError('不得拟合')), patch.object(work,'_backend',side_effect=AssertionError('不得加载模型')), patch('gaia_accretion.report_plots.render_overview',side_effect=fake_plots):
                result=reporting.build_report(run,base/'report')
            self.assertFalse(result['fit_executed'])
            self.assertEqual(before,{p.name:work.digest(p) for p in run.iterdir()})
            html=(base/'report/report.html').read_text(encoding='utf-8')
            self.assertEqual(html.count('src="data:image/png;base64,'),3)
            self.assertNotIn('<script>alert(1)</script>',html)
            self.assertIn('&lt;script&gt;',html)
            self.assertIn('未提供；未推导该量',html)
            self.assertIn('<td>0</td><td>0</td><td>0</td><td>0</td>',html)
            self.assertIn('P0=1',html)
            manifest=json.loads((base/'report/report_manifest.json').read_text())
            self.assertEqual(manifest['status'],'complete')
            self.assertIn('prediction.npz',manifest['snapshot_only'])
            self.assertNotIn('prediction.npz',manifest['preexisting_hash_verified'])

    def test_missing_prediction_does_not_trigger_fit(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);run=base/'run';saved_run(run);(run/'prediction.npz').unlink()
            with patch.object(work,'fit',side_effect=AssertionError('不得拟合')),self.assertRaises(FileNotFoundError):
                reporting.build_report(run,base/'report')
            self.assertFalse((base/'report').exists())

    def test_tampered_posterior_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);run=base/'run';saved_run(run)
            (run/'posterior.npz').write_bytes(b'changed')
            with self.assertRaises(ValueError):reporting.build_report(run,base/'report')
            self.assertFalse((base/'report').exists())

    def test_report_cannot_write_inside_original_run(self):
        with tempfile.TemporaryDirectory() as temp:
            run=Path(temp)/'run';saved_run(run)
            with self.assertRaises(ValueError):reporting.build_report(run,run/'new_report')
            self.assertFalse((run/'new_report').exists())
