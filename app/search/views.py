from app.search.SearchQuery import SearchQuery, BadQueryException

from app import app
from app.search import SearchForm
from app.provider import Provider

from flask import Blueprint, render_template, jsonify, request

from flask_api import status


# Create a search blueprint
searchbp = Blueprint("searchbp", __name__)


@searchbp.route('/search', methods=["GET"])
def search():
    search_form = SearchForm()
    gmaps_api_key = app.config['GOOGLE_MAPS_API_KEY']
    return render_template(
        'search.html',
        title='Search',
        search_form=search_form,
        GOOGLE_MAPS_API_KEY=gmaps_api_key,
    )


@searchbp.route('/search', methods=['POST'])
def results():
    query_data: dict = request.json
    if query_data is None:
        match = Provider.query.limit(30).all()
        return jsonify([provider.to_dict() for provider in match])
    query = query_data.get('query', None)
    position = query_data.get('position', None)
    search_range = query_data.get('range', None)
    try:
        search_range = float(search_range)
    except ValueError:
        search_range = None
    try:
        search_query = SearchQuery(
            query=query, position=position, search_range=search_range
        )
        search_results = search_query.search(Provider)
        return jsonify(search_results)
    except BadQueryException as e:
        response = jsonify(error=e.get_msg()), status.HTTP_400_BAD_REQUEST
        return response
