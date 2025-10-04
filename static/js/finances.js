$(document).ready(function() {
  var table = $('#finance-table').DataTable({
    ajax: {
      url: "/finances/transactions-data/",
      data: function(d) {
        d.period = $('#filter-period').val();
      }
    },
    columns: [
      { data: "date" },
      { data: "guardian" },
      {
        data: "amount",
        className: "text-right",
        render: function(data, type, row) {
          return parseFloat(data).toFixed(2);
        }
      },
      { data: "product" },
      { data: "status" }
    ],
    footerCallback: function (row, data, start, end, display) {
      var api = this.api();

      // helper
      var parse = function (i) {
        return typeof i === 'string' ?
          parseFloat(i) :
          typeof i === 'number' ?
            i : 0;
      };

      // total across all filtered data
      var overallTotal = api
        .column(2)
        .data()
        .reduce(function(a, b) {
          return parse(a) + parse(b);
        }, 0);

      // total just for this page
      var pageTotal = api
        .column(2, { page: 'current' })
        .data()
        .reduce(function(a, b) {
          return parse(a) + parse(b);
        }, 0);

      // update footers
      $('#page-total').html(pageTotal.toFixed(2));
      $('#overall-total').html(overallTotal.toFixed(2));
    }
  });

  $('#filter-period').on('change', function() {
    table.ajax.reload();
  });
});
