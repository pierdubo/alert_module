from datetime import timedelta, date
from json import dumps

import ee
from pathlib import Path
import geopandas as gpd
from ipyleaflet import GeoJSON

from sepal_ui import sepalwidgets as sw
from sepal_ui.scripts import utils as su

import ee

from component import parameter as cp
from component import widget as cw
from component.model import AlertModel
from component import scripts as cs
from component.message import cm


class AlertView(sw.Card):
    def __init__(self, aoi_model, map_):

        # init the models
        self.alert_model = AlertModel()
        self.aoi_model = aoi_model

        # wire the map object
        self.map = map_

        # select the alert collection that will be used
        self.w_alert = sw.Select(
            v_model=None,
            items=[*cp.alert_drivers],
            label=cm.view.alert.collection.label,
        )

        # select the type of alert to use in the computation
        # recent will be defined from now - X days in the past
        # historical will provide 2 date pickers
        self.w_alert_type = sw.RadioGroup(
            label="type of alerts",
            v_model=self.alert_model.alert_type,
            row=True,
            children=[
                sw.Radio(label=cm.view.alert.type.recent, value="RECENT"),
                sw.Radio(label=cm.view.alert.type.custom, value="HISTORICAL"),
            ],
        )

        # dropdown to select the lenght of the "recent" period
        self.w_recent = sw.Select(
            v_model=None, items=cp.time_delta, label=cm.view.alert.recent.label
        )

        # create a datepickers row to select the 2 historical dates
        self.w_historic = cw.DateLine().disable().hide()

        # select the minimal size of the alerts
        self.w_size = cw.SurfaceSelect()

        # set a btn to validate and load the alerts
        self.btn = sw.Btn(cm.view.alert.btn.label)

        # set an alert to display information to the end user
        self.alert = sw.Alert()

        # bind the widgets and the model
        # w_recent binding will be done manually
        (
            self.alert_model.bind(self.w_alert, "alert_collection")
            .bind(self.w_alert_type, "alert_type")
            .bind(self.w_historic.w_start, "start")
            .bind(self.w_historic.w_end, "end")
            .bind(self.w_size, "min_size")
        )

        super().__init__(
            children=[
                self.w_alert,
                self.w_alert_type,
                self.w_recent,
                self.w_historic,
                self.w_size,
                self.btn,
                self.alert,
            ],
            class_="mt-5",
            elevation=False,
        )

        # add js behaviours
        self.w_alert_type.observe(self._change_alert_type, "v_model")
        self.w_alert.observe(self._set_alert_collection, "v_model")
        self.w_recent.observe(self._set_recent_period, "v_model")
        self.btn.on_event("click", self.load_alerts)
        self.aoi_model.observe(self.remove_alerts, "name")

    def remove_alerts(self, change):
        """
        remove the alerts on name change i.e. aoi change
        The other clearing methods are trigger by the metadata and the planet tile
        """

        self.map.remove_layername("alerts")

        return

    @su.loading_button(debug=True)
    def load_alerts(self, widget, event, data):
        """load the alerts in the model"""

        # check that all variables are set
        if not all(
            [
                self.alert.check_input(
                    self.aoi_model.feature_collection, cm.view.alert.error.no_aoi
                ),
                self.alert.check_input(
                    self.alert_model.alert_collection, cm.view.alert.error.no_collection
                ),
                self.alert.check_input(
                    self.alert_model.alert_type, cm.view.alert.error.no_type
                ),
                self.alert.check_input(
                    self.alert_model.start, cm.view.alert.error.no_start
                ),
                self.alert.check_input(
                    self.alert_model.end, cm.view.alert.error.no_end
                ),
                self.alert.check_input(
                    self.alert_model.min_size, cm.view.alert.error.no_size
                ),
            ]
        ):
            return

        # clean the current display if necessary
        self.alert_model.current_id = None
        self.map.remove_layername(cm.map.layer.alerts)

        # create the grid
        grid = cs.set_grid(self.aoi_model.gdf)

        # loop in the grid to avoid timeout in the define AOI
        # display information to the user
        self.alert.update_progress(0, bar_length=20)
        data = None
        for i, geom in enumerate(grid.geometry):

            ee_geom = ee.FeatureCollection(ee.Geometry(geom.__geo_interface__))

            # load the alerts in the system
            all_alerts = cs.get_alerts(
                collection=self.alert_model.alert_collection,
                start=self.alert_model.start,
                end=self.alert_model.end,
                aoi=ee_geom,
            )

            alert_clump = cs.get_alerts_clump(
                alerts=all_alerts,
                aoi=ee_geom,
                min_size=self.alert_model.min_size,
            )

            if data is None:
                data = alert_clump.getInfo()
            else:
                data["features"] += alert_clump.getInfo()["features"]

            self.alert.update_progress(i / len(grid), bar_length=20)

        # save the clumps as a geoJson dict in the model
        gdf = gpd.GeoDataFrame.from_features(data, crs="EPSG:4326")
        gdf["review"] = cm.view.metadata.status.unset

        # order the gdf by number of pixels
        gdf = gdf.sort_values(by=["nb_pixel"], ignore_index=True, ascending=False)

        # reset the ids
        gdf["id"] = gdf.index

        # save it in the model
        self.alert_model.gdf = gdf

        # add the layer on the map
        layer = self.alert_model.get_ipygeojson()
        layer.on_click(self.on_alert_click)
        self.map.add_layer(layer)

        # reset in cas an error was displayed
        self.alert.reset()

        return self

    def on_alert_click(self, feature, **kwargs):
        """
        change the current id on click on a specif alert feature
        This change will trigger the modification of the metadata and the map zoom
        """

        self.alert_model.current_id = feature["properties"]["id"]

        return

    def _set_recent_period(self, change):
        """
        manually set the start and end traits of the model based on the number
        of days set in the w_recent. output should be 2 string values using
        the same format as the datepickers.
        """

        # exit when it's manually set to None by the alert type change
        if change["new"] is None:
            return

        today = date.today()
        past = today - timedelta(days=change["new"])

        self.alert_model.start = today.strftime("%Y-%m-%d")
        self.alert_model.end = past.strftime("%Y-%m-%d")

        return self

    def _set_alert_collection(self, change):
        """set the min and max year based on the selected data collection"""

        # init the datepicker with appropriate min and max values
        year_list = cp.alert_drivers[change["new"]]["avalaible_years"]
        self.w_historic.init(min(year_list), max(year_list))

        # unable it
        self.w_historic.unable()

        return self

    def _change_alert_type(self, change):
        """change how the end user select the time period"""

        # delete all previous values
        self.w_recent.reset()
        self.w_historic.w_start.reset()
        self.w_historic.w_end.reset()

        # exchange component visibility
        self.w_historic.toggle_viz()
        self.w_recent.toggle_viz()

        return self
