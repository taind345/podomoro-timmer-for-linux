import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Adw, Pango, PangoCairo

class ScalableTimer(Gtk.DrawingArea):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_draw_func(self.on_draw)
        self.text = "25:00"
        
    def set_text(self, text):
        self.text = text
        self.queue_draw()

    def on_draw(self, area, cr, width, height):
        layout = self.create_pango_layout(self.text)
        desc = Pango.FontDescription("Sans Bold")
        
        # Scale to fit width and height. 
        # Assume standard 25:00 string is about 5 chars.
        # Height is usually the limiting factor for short text, but let's check both.
        # Arbitrary multiplier to fill nicely:
        scale = min(width / 5.0, height / 1.5)
        if scale < 10: scale = 10
        
        desc.set_absolute_size(int(scale * Pango.SCALE))
        layout.set_font_description(desc)
        
        # Get dimensions
        ink_rect, logical_rect = layout.get_extents()
        text_width = logical_rect.width / Pango.SCALE
        text_height = logical_rect.height / Pango.SCALE
        
        # Center
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        
        cr.move_to(x, y)
        PangoCairo.show_layout(cr, layout)

class TestApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.example.Test2')

    def do_activate(self):
        win = Adw.ApplicationWindow(application=self)
        self.timer = ScalableTimer()
        self.timer.set_vexpand(True)
        self.timer.set_hexpand(True)
        
        box = Gtk.Box()
        box.append(self.timer)
        win.set_content(box)
        win.present()
        import gi.repository.GLib as GLib
        GLib.timeout_add(2000, lambda: win.close())

if __name__ == '__main__':
    app = TestApp()
    app.run(sys.argv)
