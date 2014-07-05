define([], function() {
  'use strict';

  var chart_defaults = {
    limit: 50,
    linkFormatter: function(item) {
      return item.link;
    },
    value: function(item) {
      return item.duration || 1;
    },
    className: function(item) {
      return 'result-' + item.result.id;
    }
  };

  return {
    getChartData: function getChartData(items, current, options) {
      // this should return two series, one with passes, and one with failures
      var data = new Array(options.limit),
          i, y, item, result = [];

      options = $.extend({}, chart_defaults, options || {});
      current = current || null;

      if (current) {
        items = $.merge([], items);
        items.pop();
        items.unshift(current);
      }

      for (i = 0, y = options.limit; (item = items[i]) && y > 0; i++, y--) {
        result.push({
          value: options.value(item),
          className: options.className(item),
          id: item.id,
          data: item,
          highlight: current && current.id == item.id
        });
      }

      return {
        data: result,
        options: options
      };
    }
  };
});
