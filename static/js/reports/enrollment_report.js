document.addEventListener('DOMContentLoaded', function () {
    const table = $('#enrollmentTable').DataTable({
        ajax: {
            url: '/reports/enrollment/data/',
            data: function (d) {
                d.term_filter = $('#termFilter').val();
            },
            dataSrc: function (json) {
                if (!json.summary) return json.data;

                const summaries = {
                    prev: json.summary.previous || {},
                    curr: json.summary.current || {},
                    next: json.summary.next || {},
                };

                for (const [prefix, data] of Object.entries(summaries)) {
                    $(`#${prefix}TotalPrograms`).text(data.total_programs ?? '-');
                    $(`#${prefix}TotalEnrollments`).text(data.total_enrollments ?? '-');
                    $(`#${prefix}TotalCapacity`).text(data.total_capacity ?? '-');
                    $(`#${prefix}Utilization`).text(
                        data.utilization != null ? data.utilization + '%' : '-'
                    );
                }

                return json.data;
            }  // <-- ✅ No semicolon
        },  // <-- ✅ Close ajax object

        columns: [
            {data: 'name'},
            {data: 'category'},
            {data: 'instructor'},
            {data: 'enrollments', className: 'text-center'},
            {data: 'capacity', className: 'text-center'},
            {data: 'spaces_left', className: 'text-center'}
        ],

        order: [[5, 'desc']],
        pageLength: 25,
        responsive: true,
        pagingType: 'simple_numbers',
        dom: "<'table-responsive't><'flex items-center justify-between mt-4 text-sm'<'info'i><'pagination'p>>",

        drawCallback: function () {
            $('.dataTables_paginate a').addClass('px-3 py-1 mx-1 border rounded text-blue-600 hover:bg-blue-100');
            $('.dataTables_paginate .current').addClass('bg-blue-600 text-white');
        },

        initComplete: function () {
            const api = this.api();
            api.columns([0, 1, 2]).every(function (index) {
                const column = this;
                const input = $(`.column-filter[data-index="${index}"]`);
                input.off('keyup change clear');
                input.on('keyup change clear', function () {
                    if (column.search() !== this.value) {
                        column.search(this.value).draw();
                    }
                });
            });
        }
    });  // <-- ✅ close DataTable config

    $('#termFilter').on('change', function () {
        table.ajax.reload();
    });

    function selectTerm(value) {
    // Update hidden filter and reload
    document.getElementById('termFilter').value = value;
    $('#termFilter').trigger('change');

    // Update the "Showing:" label
    const labels = {
        previous: "Previous Term",
        current: "Current Term",
        next: "Next Term"
    };
    $('#selectedTermLabel').text("Showing: " + labels[value]);

    // 🔵 Highlight the active button
    $('.term-select').removeClass('bg-blue-100 font-semibold text-blue-800');
    $(`.term-select[data-term="${value}"]`).addClass('bg-blue-100 font-semibold text-blue-800');
}
window.selectTerm = selectTerm; // 👈 make it global

});  // <-- ✅ close DOMContentLoaded