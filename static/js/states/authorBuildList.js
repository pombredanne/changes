define([
  'app',
  'utils/parseLinkHeader',
  'utils/sortBuildList'
], function(app, parseLinkHeader, sortBuildList) {
  'use strict';

  return {
    parent: 'layout',
    url: '/my/builds/',
    templateUrl: 'partials/author-build-list.html',
    controller: function($scope, $http, buildList, authData, Collection, CollectionPoller, PageTitle) {
      PageTitle.set('My Builds');

      function addBuild(data) {
        $scope.$apply(function() {
          var updated = false,
              item_id = data.id,
              attr, result, item;

          if ($scope.builds.length > 0) {
            result = $.grep($scope.builds, function(e){ return e.id == item_id; });
            if (result.length > 0) {
              item = result[0];
              for (attr in data) {
                // ignore dateModified as we're updating this frequently and it causes
                // the dirty checking behavior in angular to respond poorly
                if (item[attr] != data[attr] && attr != 'dateModified') {
                  updated = true;
                  item[attr] = data[attr];
                }
                if (updated) {
                  item.dateModified = data.dateModified;
                }
              }
            }
          }
          if (!updated) {
            $scope.builds.unshift(data);
            sortBuildList($scope.builds);
            $scope.builds = $scope.builds.slice(0, 100);
          }
        });
      }

      function loadBuildList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.builds = sortBuildList(data);
            $scope.pageLinks = parseLinkHeader(headers('Link'));
          });
      }

      $scope.loadPreviousPage = function() {
        $(document.body).scrollTop(0);
        loadBuildList($scope.pageLinks.previous);
      };

      $scope.loadNextPage = function() {
        $(document.body).scrollTop(0);
        loadBuildList($scope.pageLinks.next);
      };

      $scope.$watch("pageLinks", function(value) {
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;
      });

      $scope.pageLinks = parseLinkHeader(buildList.headers('Link'));

      $scope.builds = new Collection(buildList.data, {
        sortFunc: sortBuildList,
        limit: 100
      });

      var poller = new CollectionPoller({
        $scope: $scope,
        collection: $scope.builds,
        endpoint: '/api/0/authors/me/builds/',
        shouldUpdate: function(item, existing) {
          if (existing.dateModified < item.dateModified) {
            return true;
          }
          return false;
        }
      });
    },
    resolve: {
      buildList: function($http) {
        return $http.get('/api/0/authors/me/builds/');
      }
    }
  };
});
