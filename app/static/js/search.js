const search_bar = document.getElementById("search-bar");

function generateSearchQuery() {
  const query_string = search_bar.querySelector("#query").value;
  var cLatLng = currentPos;
  var range = 30; // Stub
  const range_option = search_bar.querySelector("#search_range");
  if (range_option !== null && range_option.value !== "") {
    range = range_option.value;
  }
  var query = { query: query_string, position: cLatLng, range: range };
  console.log(query);
  return query;
}

// Init the SearchBar actions
function initSearchBar(func) {
  var search_icon = document.getElementById("search-icon");
  search_icon.onclick = function(event) {
    query = generateSearchQuery();
    func(query);
  };
  search_bar.onkeydown = function(event) {
    if (event.keyCode === 13) {
      event.preventDefault();
      search_bar.blur();
      query = generateSearchQuery();
      func(query);
    }
  };
}

function search(query) {
  // Now construct the query url:
  query = JSON.stringify(query);
  const url = "/search?data=" + encodeURIComponent(query);
  window.location = url;
}

function searchResults(query) {
  query = JSON.stringify(query);

  var xhr = new XMLHttpRequest();
  xhr.addEventListener("readystatechange", function() {
    if (this.readyState === 4) {
      clearResults();
      const results_list = JSON.parse(this.responseText);
      for (let i = 0; i < results_list.length; i++) {
        var result = results_list[i];
        showResult(result);
        var pos = map.getCenter();
        currentPos.lat = pos.lat();
        currentPos.lng = pos.lng();
      }
    }
  });
  xhr.open("POST", "/search");
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.send(query);
}
