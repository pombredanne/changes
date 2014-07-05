define([
  'app',
  'utils/parseLinkHeader'
], function(app, parseLinkHeader) {
  'use strict';

  return {
    parent: 'layout',
    url: '/nodes/',
    templateUrl: 'partials/node-list.html',
    controller: function($scope, $http, nodeList, Collection, PageTitle) {
      function loadNodeList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.nodeList = new Collection(data, {
              limit: 100
            });
            $scope.pageLinks = parseLinkHeader(headers('Link'));
          });
      }

      $scope.loadPreviousPage = function() {
        $(document.body).scrollTop(0);
        loadNodeList($scope.pageLinks.previous);
      };

      $scope.loadNextPage = function() {
        $(document.body).scrollTop(0);
        loadNodeList($scope.pageLinks.next);
      };

      $scope.$watch("pageLinks", function(value) {
        $scope.nextPage = value.next || null;
        $scope.previousPage = value.previous || null;
      });

      $scope.pageLinks = parseLinkHeader(nodeList.headers('Link'));

      $scope.nodeList = new Collection(nodeList.data);

      PageTitle.set('Nodes');
    },
    resolve: {
      nodeList: function($http, $stateParams) {
        return $http.get('/api/0/nodes/?since=7');
      }
    }
  };
});
