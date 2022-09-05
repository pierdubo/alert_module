from ipyleaflet import WidgetControl
from ipywidgets import Button, Layout
from sepal_ui import mapping as sm

from component.message import cm


class AlertMap(sm.SepalMap):
    def __init__(self):

        super().__init__(dc=True, zoom=3)

        self.hide_dc()

        # add the fullscreen button
        fullscreen = sm.FullScreenControl(
            self, position="topright", fullscreen=True, fullapp=True
        )
        self.add_control(fullscreen)

        # add the buttons on the topleft side of the map
        self.metadata_btn = sm.MapBtn("fas fa-info")
        self.add_widget_as_control(self.metadata_btn, "topleft")

    def add_widget_as_control(self, widget, position, first=False):
        """
        Add widget as control in the given position

        Args:
            widget (dom.widget): Widget to convert as map control
            position (str): 'topleft', 'topright', 'bottomright', 'bottomlreft'
            first (Bool): Whether set the control as first or last element
        """

        new_control = WidgetControl(
            widget=widget, position=position, transparent_bg=True
        )

        if first == True:

            self.controls = tuple(
                [new_control] + [control for control in self.controls]
            )
        else:

            self.controls = self.controls + tuple([new_control])

        return
