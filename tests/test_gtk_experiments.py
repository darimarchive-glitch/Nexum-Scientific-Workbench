"""Optional native GTK integration checks; run in a desktop or virtual display."""
import unittest

try:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gtk, Adw, Gdk, GLib
    AVAILABLE = bool(Gtk.init_check() and Gdk.Display.get_default())
except (ImportError, ValueError):
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, "GTK4/libadwaita e display não estão disponíveis")
class GtkExperimentTests(unittest.TestCase):
    def setUp(self):
        Adw.init()
        from nexum.ui.experiments_page import ExperimentsPage
        self.page = ExperimentsPage(None)

    def tearDown(self):
        self.page._pause(set_status=False)

    def test_static_benches_hide_playback_controls_and_update_on_edit(self):
        page = self.page
        for index, key, value in ((4, "pressure_bar", "1"), (5, "concentration_m", "0,02")):
            page._select_experiment(index, sync_list=True)
            before = dict(page.session.state)
            for widget in (page.start, page.pause, page.step, page.reset, page.progress, page.timeline_box):
                self.assertFalse(widget.get_visible())
            self.assertTrue(page.live_label.get_visible())
            page.fields[key].set_text(value)
            self.assertNotEqual(before, page.session.state)
            self.assertFalse(page.error_label.get_visible())

    def test_play_pause_manual_drop_and_new_parameters(self):
        page = self.page
        page._select_experiment(1, sync_list=True)
        page._start()
        self.assertTrue(page.running)
        self.assertGreater(page.timer_id, 0)
        self.assertFalse(page.config_group.get_sensitive())
        page._pause()
        self.assertFalse(page.running)
        self.assertEqual(page.timer_id, 0)
        self.assertTrue(page.config_group.get_sensitive())
        page._step()
        self.assertAlmostEqual(page.session.state["base_added_ml"], .05)
        page.fields["acid_v_ml"].set_text("40")
        self.assertEqual(page.session.elapsed, 0)
        self.assertEqual(page.session.state["liquid_volume_ml"], 40)
        self.assertEqual(len(page.session.history), 1)

    def test_invalid_edit_does_not_show_stale_measurements_or_allow_play(self):
        page = self.page
        page.fields["n"].set_text("nan")
        self.assertIsNone(page.session)
        self.assertFalse(page.start.get_sensitive())
        self.assertEqual(page.metric_rows, [])
        self.assertTrue(page.error_label.get_visible())
        page.fields["n"].set_text("2")
        self.assertIsNotNone(page.session)
        self.assertTrue(page.start.get_sensitive())
        self.assertFalse(page.error_label.get_visible())

    def test_equivalence_and_time_scrubbing_update_the_same_state(self):
        page = self.page
        page._select_experiment(1, sync_list=True)
        page._go_equivalence()
        self.assertAlmostEqual(page.session.state["ph"], 7)
        self.assertAlmostEqual(page.timeline.get_value(), 50)
        page.timeline.set_value(75)
        self.assertFalse(page.running)
        self.assertAlmostEqual(page.session.state["base_added_ml"], 37.5)
        self.assertEqual(page.session.history[-1], page.session.point)

    def test_switching_and_unmapping_stop_the_clock(self):
        page = self.page
        page._start()
        old_timer = page.timer_id
        page._select_experiment(6, sync_list=True)
        self.assertEqual(page.timer_id, 0)
        self.assertIsNone(GLib.MainContext.default().find_source_by_id(old_timer))
        self.assertEqual(page.session.elapsed, 0)
        page._start()
        page._on_unmap()
        self.assertFalse(page.running)
        self.assertEqual(page.timer_id, 0)

    def test_reaching_end_reenables_inputs_and_repeat_restarts(self):
        page = self.page
        page.fields["duration_s"].set_text("0.01")
        page._start()
        # Exercise the real timer callback with an elapsed interval.
        page.last_clock -= 1
        timer = page.timer_id
        self.assertFalse(page._tick())
        GLib.source_remove(timer)  # Manual invocation did not dispatch GLib's source.
        self.assertTrue(page.session.complete)
        self.assertFalse(page.running)
        self.assertTrue(page.config_group.get_sensitive())
        page._start()
        self.assertEqual(page.session.elapsed, 0)
        self.assertTrue(page.running)


if __name__ == "__main__":
    unittest.main()
