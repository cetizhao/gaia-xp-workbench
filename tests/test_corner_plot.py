"""SpT分箱去掉绘图伪空列，同时保留真实未占据节点。"""
import unittest

import numpy as np
from gaia_accretion.report_plots import _spt_bin_edges


class CornerPlotTests(unittest.TestCase):
    def test_discrete_nodes_keep_all_mass_without_artificial_gaps(self):
        nodes = np.arange(64.5, 67.75 + .0625, .125)
        counts = np.arange(1, len(nodes) + 1)
        samples = np.repeat(nodes, counts)
        original = samples.copy()
        old_counts, _ = np.histogram(samples, bins=32)
        self.assertTrue(np.any(old_counts == 0))
        edges = _spt_bin_edges(samples)
        actual, _ = np.histogram(samples, bins=edges)
        np.testing.assert_array_equal(actual, counts)
        np.testing.assert_array_equal(samples, original)
        np.testing.assert_allclose((edges[:-1] + edges[1:])/2, nodes)

    def test_unoccupied_middle_grid_node_remains_empty(self):
        samples = np.repeat([65., 65.125, 65.375], [3, 5, 7])
        counts, _ = np.histogram(samples, bins=_spt_bin_edges(samples))
        np.testing.assert_array_equal(counts, [3, 5, 0, 7])

    def test_continuous_and_single_node_samples_keep_all_mass(self):
        for samples in (np.linspace(65, 67, 8000), np.full(30, 66.)):
            counts, _ = np.histogram(samples, bins=_spt_bin_edges(samples))
            self.assertEqual(counts.sum(), len(samples))
