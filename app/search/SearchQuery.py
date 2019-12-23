from app.provider import Provider
from math import cos, pi, asin

from google.cloud import language_v1
from google.cloud.language_v1 import enums
from geocoder import google as google_geocode

from sqlalchemy import or_, and_

ENTITY_TYPE = enums.Entity.Type

EXCLUDE_ENTITY_TYPES = {
    ENTITY_TYPE.PHONE_NUMBER,
    ENTITY_TYPE.ADDRESS,
    ENTITY_TYPE.LOCATION,
    ENTITY_TYPE.NUMBER,
    ENTITY_TYPE.DATE,
    ENTITY_TYPE.EVENT,
    ENTITY_TYPE.PRICE,
}

COMMON_STRINGS = {"doctor", "hospital", "doctors", "hospitals"}


class BadQueryException(Exception):
    def __init__(self, msg=None):
        self._msg = msg
        super(Exception, msg)

    def get_msg(self):
        return self._msg


class SearchQuery:

    NLP_CLIENT = language_v1.LanguageServiceClient()

    def __init__(self, query: str = None, position: dict = None, search_range=None):
        self.query = query
        self.position = position
        self.range = search_range
        if position is not None and position.keys() != {'lat', 'lng'}:
            raise BadQueryException("Malformed SearchQuery")
        if query is None or query == '':
            if position is None or range is None:
                raise BadQueryException("Malformed SearchQuery")
            self.parsed_query = {'address': None,
                                 'locations': [], 'strings': []}
        else:
            self.parsed_query = self.__parse_query(query)

    def search(self, provider: Provider.__class__):
        query = provider.query
        # Strings
        string_filters = []
        strings = self.parsed_query['strings']
        partial_count = 0
        if len(strings) > 0:
            for col in [
                provider.name,
                provider.address,
                provider.speciality,
                provider.city,
                provider.state,
            ]:
                string_filters.append(or_(col.ilike(string)
                                          for string in strings))
            query = query.filter(or_(*string_filters))
        # Location
        if self.parsed_query['address'] is not None:
            # Address - singular location
            bbox = self.parsed_query['address'].bbox
            query = query.filter(self.__in_bbox(provider, bbox))
            matches = [match.to_dict() for match in query.limit(30).all()]
        elif len(self.parsed_query['locations']) > 0:
            # Locations - Union of locations
            location_filters = []
            for location in self.parsed_query['locations']:
                bbox = location.bbox
                location_filters.append(self.__in_bbox(provider, bbox))
            query = query.filter(or_(*location_filters))
            matches = [match.to_dict() for match in query.limit(30).all()]
        elif (
            self.position is not None and self.range is not None
        ):

            def dist(lat, lng):
                p = pi / 180
                lat1, lng1 = self.position['lat'] * p, self.position['lng'] * p
                lat, lng = lat * p, lng * p
                a = (
                    0.5
                    - (cos((lat - lat1)) / 2)
                    + (cos(lat) * cos(lat1) * (1 - cos(lng - lng1)) / 2)
                )
                return 12742 * asin(a ** 0.5)

            matches = [match.to_dict() for match in query.all()]
            matches = list(
                filter(lambda m: dist(m['lat'], m['lng'])
                       <= self.range, matches)
            )
        else:
            matches = [match.to_dict() for match in query.all()]
        return matches

    @staticmethod
    def __in_bbox(provider: Provider.__class__, bbox):
        (n, e), (s, w) = bbox['northeast'], bbox['southwest']
        return and_(
            provider.lat <= n, provider.lat >= s, provider.lng <= e, provider.lng >= w
        )

    @staticmethod
    def __parse_query(query):
        type_ = enums.Document.Type.PLAIN_TEXT
        document = {'content': query, 'type': type_}
        encoding_type = enums.EncodingType.UTF8

        nlp_entities = SearchQuery.NLP_CLIENT.analyze_entities(
            document, encoding_type=encoding_type
        ).entities

        address_entity = [
            e.name for e in nlp_entities if e.type == ENTITY_TYPE.ADDRESS]
        address_geocode = (
            google_geocode(address_entity[0]) if len(
                address_entity) > 0 else None
        )
        address = None
        if address_geocode is not None and address_geocode.ok:
            address = address_geocode.current_result
        location_entities = [
            e.name for e in nlp_entities if e.type == ENTITY_TYPE.LOCATION
        ]
        locations = []
        if address is None and len(location_entities) > 0:
            locations_geocode = [google_geocode(
                loc) for loc in location_entities]
            locations = [
                loc.current_result for loc in locations_geocode if loc.ok]
        other_entities = [
            e.name.lower() for e in nlp_entities if e.type not in EXCLUDE_ENTITY_TYPES
        ]

        strings = [s for s in other_entities if s not in COMMON_STRINGS]

        parsed_query = {'address': address,
                        'locations': locations, 'strings': strings}
        return parsed_query
