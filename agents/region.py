import json
from shapely.geometry import Point, shape
from collections import defaultdict


class Region:
    """Collects taxes and applies to ameliorate quality of life"""

    def __init__(self, region, index=1, gdp=0, pop=0, total_commute=0, licenses=0):
        # A region is an OSGEO object that contains Fields and Geometry
        # For Spanish adaptation, 'region' is expected to be a GeoSeries/GeoDataFrame row or similar
        # object with 'geometry' and 'id' (as mun_code) and potentially 'NAME' attributes.
        self.address_envelope = region.geometry.envelope # Assuming region.geometry is a shapely geometry
        self.addresses = region.geometry # Store the shapely geometry directly
        self.id = str(region.id) # Should be the 5-digit INE code for Spanish municipalities
        
        # If region.geometry is not already a shapely object, conversion might be needed
        # For example, if it's WKT: from shapely.wkt import loads; self.addresses = loads(region.geometry_wkt_column)
        # If it's GeoJSON dict: self.addresses = shape(region.geometry_geojson_dict_column)
        # The original code used: shape(json.loads(self.addresses.ExportToJson())) which implies an OGR object.
        # If 'region.geometry' is already a shapely object from GeoPandas, this direct assignment is fine.

        # Attempt to get a name for the region, fallback to ID if not available
        if hasattr(region, 'NAME'): # Common in GeoDataFrames from shapefiles/GeoJSON
            self.name = str(region.NAME)
        elif hasattr(region, 'NOMBRE'): # Common in Spanish datasets
            self.name = str(region.NOMBRE)
        else:
            self.name = f"Region_{self.id}" # Fallback name

        self.index = index
        self.gdp = gdp
        self.pop = pop
        self.licenses = licenses
        self.total_commute = total_commute
        self.cumulative_treasure = defaultdict(int)
        self.treasure = defaultdict(int)
        self.applied_treasure = defaultdict(int)
        self.registry = defaultdict(list)

    @property
    def license_price(self):
        return self.index

    @property
    def total_treasure(self):
        return sum(self.treasure.values())

    def collect_taxes(self, amount, key):
        self.treasure[key] += amount

    def save_and_clear_treasure(self):
        for key in self.treasure.keys():
            self.cumulative_treasure[key] += self.treasure[key]
            self.treasure[key] = 0

    def transfer_treasure(self):
        treasure = self.treasure.copy()
        self.save_and_clear_treasure()
        return treasure

    def update_index_pop(self, proportion_pop):
        """First term of QLI update, relative to change in population within its territory"""
        self.index *= proportion_pop

    def update_applied_taxes(self, amount, key):
        self.applied_treasure[key] += amount

    def update_index(self, value):
        """Index is updated per capita for current population"""
        self.index += value

    def __repr__(self):
        # Use self.name if it was successfully initialized, otherwise self.id
        name_to_display = self.name if hasattr(self, 'name') and self.name else self.id
        return '%s \n QLI: %.2f, \t GDP: %.2f, \t Pop: %s, Commute: %.2f' % (name_to_display, self.index, self.gdp,
                                                                             self.pop, self.total_commute)
