from flask import request, jsonify

from .helpers.marshmallow import marshal
from .helpers.flask import abort


def make_metadata_api(classification, metadata_schema):
    """Since all metadata APIs look very similar, this function just generates
    the function that'll handle the API endpoint for an entity. It generates a
    function that handles both /metadata/entity/ and /metadata/entity/<id>."""

    def metadata_api(entity_id):
        """Get all :py:class:`~colombia.models.Metadata` s or a single one with the
        given id.

        :param id: Entity id, see :py:class:`colombia.models.Metadata.id`
        :type id: int
        :code 404: Entity doesn't exist
        """
        if entity_id is not None:
            q = classification.get_by_id(entity_id)
            return marshal(metadata_schema, q, many=False)
        else:
            level = request.args.get("level", None)
            q = classification.get_all(level=level)
            return marshal(metadata_schema, q)

    def hierarchy_api():
        """Get the mapping of ids from a level of a classification to another
        level.

        :param from_level: Entity level, see :py:class:`colombia.models.Metadata.level`
        :param to_level: Entity level, see :py:class:`colombia.models.Metadata.level`
        :type from_level: str
        :type to_level: str
        """
        from_level = request.args.get("from_level", classification.levels[-1])
        to_level = request.args.get("to_level", classification.levels[0])

        try:
            mapping = classification.aggregation_mapping(from_level, to_level)
        except (AssertionError, ValueError):
            abort(400, """Levels you gave me seem invalid. Are you sure
                  from_level is lower than to_level and either are valid
                  levels?""", payload=classification.levels)

        return jsonify(data=mapping)

    return metadata_api, hierarchy_api


def register_metadata_apis(app, entities, metadata_schema):
    """Given an entity class, generate an API handler and register URL routes
    with flask. """

    for entity_name, settings in entities.items():

        # Generate handler function for entity
        metadata_api_func, hierarchy_api_func = make_metadata_api(settings["classification"], metadata_schema)

        # Singular endpoint e.g. /entity/7
        app.add_url_rule(
            "/{entity_name}/<int:entity_id>".format(entity_name=entity_name),
            endpoint=entity_name + "_singular",
            view_func=metadata_api_func
        )

        # List endpoint e.g. /entity/
        app.add_url_rule(
            "/{entity_name}/".format(entity_name=entity_name),
            endpoint=entity_name + "_all",
            view_func=metadata_api_func,
            defaults={"entity_id": None}
        )

        # Hierarchy endpoint e.g. /entity/hierarchy?from_level=blah&to_level=blah2
        app.add_url_rule(
            "/{entity_name}/hierarchy".format(entity_name=entity_name),
            endpoint=entity_name + "_hierarchy",
            view_func=hierarchy_api_func,
        )

    return app