document.addEventListener('DOMContentLoaded', function () {
    let enrollmentData = [];

    function createMobileCards(data) {
        const mobileContainer = document.getElementById('mobileCards');
        if (!mobileContainer) {
            return;
        }

        if (!data || data.length === 0) {
            mobileContainer.innerHTML = '<div class="p-4 text-center text-gray-500">No enrollment data available</div>';
            return;
        }

        const cardsHtml = data.map(item => `
            <div class="bg-gradient-to-r from-white to-gray-50 border border-gray-200 rounded-lg p-4 shadow-sm">
                <div class="flex justify-between items-start mb-3">
                    <h4 class="font-semibold text-gray-900 text-lg">${item.name}</h4>
                    <span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full">${item.category}</span>
                </div>

                <div class="space-y-2 mb-3">
                    <div class="flex items-center">
                        <span class="w-2 h-2 bg-purple-500 rounded-full mr-2"></span>
                        <span class="text-sm text-gray-600">Instructor: <span class="font-medium text-gray-900">${item.instructor}</span></span>
                    </div>
                    <div class="flex items-center">
                        <span class="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                        <span class="text-sm text-gray-600">Day: <span class="font-medium text-gray-900">${item.day}</span></span>
                    </div>
                </div>

                <div class="grid grid-cols-3 gap-3">
                    <div class="text-center p-2 bg-green-50 rounded-lg border border-green-200">
                        <div class="text-lg font-bold text-green-700">${item.enrollments}</div>
                        <div class="text-xs text-green-600 uppercase tracking-wide">Enrolled</div>
                    </div>
                    <div class="text-center p-2 bg-orange-50 rounded-lg border border-orange-200">
                        <div class="text-lg font-bold text-orange-700">${item.capacity}</div>
                        <div class="text-xs text-orange-600 uppercase tracking-wide">Capacity</div>
                    </div>
                    <div class="text-center p-2 bg-red-50 rounded-lg border border-red-200">
                        <div class="text-lg font-bold text-red-700">${item.spaces_left}</div>
                        <div class="text-xs text-red-600 uppercase tracking-wide">Available</div>
                    </div>
                </div>
            </div>
        `).join('');

        mobileContainer.innerHTML = `<div class="space-y-4">${cardsHtml}</div>`;
    }

    function createTabletTable(data) {
        const tabletTable = document.getElementById('enrollmentTableTablet');
        if (!tabletTable) {
            return;
        }

        const tbody = tabletTable.querySelector('tbody');
        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="px-4 py-3 text-center text-gray-500">No enrollment data available</td></tr>';
            return;
        }

        const rowsHtml = data.map(item => `
            <tr class="hover:bg-blue-50 transition-colors duration-150">
                <td class="px-4 py-3 whitespace-nowrap">
                    <div class="font-medium text-gray-900">${item.name}</div>
                    <div class="text-sm text-gray-500">${item.category}</div>
                    <div class="text-xs text-purple-600">${item.instructor}</div>
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-center">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        ${item.day}
                    </span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-center">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        ${item.enrollments}
                    </span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-center">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                        ${item.capacity}
                    </span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap text-center">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${item.spaces_left <= 5 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}">
                        ${item.spaces_left}
                    </span>
                </td>
            </tr>
        `).join('');

        tbody.innerHTML = rowsHtml;
    }

    const table = $('#enrollmentTable').DataTable({
        ajax: {
            url: '/reports/enrollment/data/',
            data: function (d) {
                d.term_filter = $('#termFilter').val();
            },
            dataSrc: function (json) {
                const sel = $('#termFilter').val() || 'current';
                const sum = (json.summary && json.summary[sel]) ? json.summary[sel] : {};
                $('#totalPrograms').text(sum.total_programs ?? 0);
                $('#totalEnrollments').text(sum.total_enrollments ?? 0);
                $('#totalCapacity').text(sum.total_capacity ?? 0);
                $('#overallUtilization').text(((sum.utilization ?? 0)) + '%');

                enrollmentData = json.data;
                createMobileCards(enrollmentData);
                createTabletTable(enrollmentData);

                return json.data;
            }
        },
        columns: [
            {data: 'name', className: 'px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900', orderable: false},
            {
                data: 'category',
                className: 'px-6 py-4 whitespace-nowrap text-sm text-indigo-600 font-medium',
                render: function (data, type) {
                    if (type === 'display' || type === 'filter') {
                        return data;
                    }
                    return (data || '').toString().toLowerCase();
                }
            },
            {
                data: 'day',
                className: 'px-6 py-4 whitespace-nowrap text-sm text-blue-600 font-medium',
                render: function (data, type) {
                    if (type === 'display' || type === 'filter') {
                        return data;
                    }
                    return (data || '').toString().toLowerCase();
                }
            },
            {
                data: 'instructor',
                className: 'px-6 py-4 whitespace-nowrap text-sm text-purple-600 font-medium',
                render: function (data, type) {
                    if (type === 'display' || type === 'filter') {
                        return data;
                    }
                    return (data || '').toString().toLowerCase();
                }
            },
            {
                data: 'enrollments',
                className: 'px-6 py-4 whitespace-nowrap text-sm text-center font-bold text-green-700',
                render: function (data, type) {
                    const value = Number(data) || 0;
                    if (type === 'display') {
                        return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">${value}</span>`;
                    }
                    return value;
                }
            },
            {
                data: 'capacity',
                className: 'px-6 py-4 whitespace-nowrap text-sm text-center font-bold text-orange-700',
                render: function (data, type) {
                    const value = Number(data) || 0;
                    if (type === 'display') {
                        return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">${value}</span>`;
                    }
                    return value;
                }
            },
            {
                data: 'spaces_left',
                className: 'px-6 py-4 whitespace-nowrap text-sm text-center font-bold',
                render: function (data, type) {
                    const value = Number(data) || 0;
                    if (type === 'display') {
                        const colorClass = value <= 5 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800';
                        return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}">${value}</span>`;
                    }
                    return value;
                }
            }
        ],
        order: [[4, 'desc']],
        pageLength: 25,
        responsive: false,
        pagingType: 'simple_numbers',
        dom: "<'flex flex-col sm:flex-row sm:items-center sm:justify-between mt-4 px-6 py-3'<'text-sm text-gray-700'i><'mt-2 sm:mt-0'p>>t",
        language: {
            info: 'Showing _START_ to _END_ of _TOTAL_ entries',
            paginate: {
                previous: '‹ Previous',
                next: 'Next ›'
            }
        },
        drawCallback: function () {
            $('.dataTables_paginate').addClass('flex justify-center space-x-1');
            $('.dataTables_paginate a').addClass('px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 hover:text-gray-700 transition-colors duration-150');
            $('.dataTables_paginate .current').addClass('bg-blue-600 text-white border-blue-600 hover:bg-blue-700');
            $('#enrollmentTable tbody tr').addClass('hover:bg-blue-50 transition-colors duration-150');
        },
        initComplete: function () {
            const api = this.api();
            api.columns([0, 1, 2, 3]).every(function (index) {
                const column = this;
                const input = $(`.column-filter[data-index="${index}"]`);
                if (!input.length) {
                    return;
                }
                input.off('keyup change clear');
                input.on('keyup change clear', function () {
                    if (column.search() !== this.value) {
                        column.search(this.value).draw();
                    }
                });
            });
        }
    });

    $('#termFilter').on('change', function () {
        table.ajax.reload();
    });
});
