from .interfaces import ILookupStrategy

from sqlalchemy import inspect
from .core import db


class SQLAlchemyLookup(ILookupStrategy):
    """Look up a query in an SQLAlchemy model."""

    def __init__(self, model):
        self.model = model

    def get_column_by_name(self, name):
        column = getattr(self.model, name, None)
        if column is None:
            raise ValueError(
                "Column {} doesn't exist on model {}".format(name, self.model)
            )
        return column

    def get_all_model_columns(self):
        return [x for x in inspect(self.model).columns]

    def fetch(self, slice_def, query):
        # Build a lost of predicates
        # e.g. location_id==5 AND product_level=='4digit'

        filter_predicates = []
        for query_facet in query["arguments"].values():

            # Get column name e.g. "location_id", and corresponding column
            # object, e.g. model.location_id
            key_column = self.get_column_by_name(query_facet["field_name"])

            # Generate predicate e.g. model.location_id==5
            predicate = key_column == query_facet["value"]
            filter_predicates.append(predicate)

            # Do the same for the "level"
            level_column_name = query_facet.get(
                "level_field_name",
                query_facet["field_name"][:-3]
                + "_level",  # TODO: blah_id to blah_level
            )
            level_column = self.get_column_by_name(level_column_name)
            level_predicate = level_column == query_facet["level"]
            filter_predicates.append(level_predicate)
            # TODO: how do we specify levels that don't need to be filtered by,
            # if the data already is partitioned? (e.g. geolevels)

        # Filter by result level also
        level_column = self.get_column_by_name(
            query["result"]["field_name"][:-3] + "_level"
        )
        level_predicate = level_column == query["result"]["level"]
        filter_predicates.append(level_predicate)

        # Filter by year ranges
        year_column = self.get_column_by_name("year")

        if query["year_range"]["start"]:
            start_predicate = year_column >= query["year_range"]["start"]
            filter_predicates.append(start_predicate)

        if query["year_range"]["end"]:
            end_predicate = year_column <= query["year_range"]["end"]
            filter_predicates.append(end_predicate)

        q = (
            db.session.query(*self.get_all_model_columns())
            .filter(*filter_predicates)
            .all()
        )

        return q


class DataFrameLookup(ILookupStrategy):
    """Look up a query in a pandas dataframe."""

    def __init__(self, df):
        self.df = df

    def fetch(self, slice_def, query):
        raise NotImplementedError()
