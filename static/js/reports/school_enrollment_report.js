document.addEventListener('DOMContentLoaded', function () {
  const $ = window.jQuery;
  if (!$ || !$.fn.DataTable) {
    console.warn('school_enrollment_report.js: jQuery DataTables is required but not available.');
    return;
  }

  const dataTableElement = document.getElementById('schoolEnrollmentTable');
  if (!dataTableElement) {
    return;
  }

  const dataUrl = dataTableElement.dataset.sourceUrl;
  if (!dataUrl) {
    console.warn('school_enrollment_report.js: missing data-source-url on #schoolEnrollmentTable.');
    return;
  }

  let dataset = [];

  function createMobileCards(data) {
    const container = document.getElementById('mobileCards');
    if (!container) {
      return;
    }

    if (!data || data.length === 0) {
      container.innerHTML = '<div class="p-4 text-center text-gray-500">No enrolment data available</div>';
      return;
    }

    container.innerHTML = '<div class="space-y-4">' + data.map(item => `
      <div class="bg-gradient-to-r from-white to-amber-50 border border-amber-200 rounded-lg p-4 shadow-sm">
        <div class="flex justify-between items-start mb-3">
          <div>
            <h4 class="font-semibold text-gray-900 text-lg">${item.name}</h4>
            <p class="text-sm text-amber-700">${item.school}</p>
          </div>
          <span class="px-2 py-1 bg-amber-100 text-amber-800 text-xs font-medium rounded-full">${item.category}</span>
        </div>
        <p class="text-sm text-gray-500 mb-3">${item.schedule || 'Schedule TBC'}</p>
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
    `).join('') + '</div>';
  }

  function createTabletTable(data) {
    const table = document.getElementById('schoolEnrollmentTableTablet');
    if (!table) {
      return;
    }

    const tbody = table.querySelector('tbody');
    if (!tbody) {
      return;
    }

    if (!data || data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" class="px-4 py-3 text-center text-gray-500">No enrolment data available</td></tr>';
      return;
    }

    tbody.innerHTML = data.map(item => `
      <tr class="hover:bg-amber-50 transition-colors duration-150">
        <td class="px-4 py-3 whitespace-nowrap">
          <div class="font-medium text-gray-900">${item.name}</div>
          <div class="text-sm text-gray-500">${item.category}</div>
          <div class="text-xs text-amber-600">${item.schedule || 'Schedule TBC'}</div>
        </td>
        <td class="px-4 py-3 whitespace-nowrap text-gray-700">${item.school}</td>
        <td class="px-4 py-3 whitespace-nowrap text-center">
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">${item.enrollments}</span>
        </td>
        <td class="px-4 py-3 whitespace-nowrap text-center">
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">${item.capacity}</span>
        </td>
      </tr>
    `).join('');
  }

  const dataTable = $(dataTableElement).DataTable({
    ajax: {
      url: dataUrl,
      data(d) {
        d.term_filter = $('#termFilter').val();
        d.school_id = $('#schoolFilter').val();
        d.day = $('#dayFilter').val();
      },
      dataSrc(json) {
        const key = $('#termFilter').val() || 'current';
        const summary = (json.summary && json.summary[key]) ? json.summary[key] : {};
        $('#totalPrograms').text(summary.total_programs ?? 0);
        $('#totalEnrollments').text(summary.total_enrollments ?? 0);
        $('#totalCapacity').text(summary.total_capacity ?? 0);
        $('#overallUtilization').text((summary.utilization ?? 0) + '%');

        dataset = json.data || [];
        createMobileCards(dataset);
        createTabletTable(dataset);
        return json.data;
      }
    },
    columns: [
      {data: 'name', className: 'px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900'},
      {data: 'school', className: 'px-6 py-4 whitespace-nowrap text-sm text-amber-700 font-medium'},
      {data: 'category', className: 'px-6 py-4 whitespace-nowrap text-sm text-amber-600'},
      {data: 'schedule', className: 'px-6 py-4 whitespace-nowrap text-sm text-gray-600'},
      {
        data: 'enrollments',
        className: 'px-4 py-4 whitespace-nowrap text-sm text-center font-bold text-green-700',
        render(data) {
          return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">${data}</span>`;
        }
      },
      {
        data: 'capacity',
        className: 'px-4 py-4 whitespace-nowrap text-sm text-center font-bold text-orange-700',
        render(data) {
          return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">${data}</span>`;
        }
      },
      {
        data: 'spaces_left',
        className: 'px-4 py-4 whitespace-nowrap text-sm text-center font-bold',
        render(data) {
          const cls = data <= 5 ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800';
          return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}">${data}</span>`;
        }
      }
    ],
    order: [[4, 'desc']],
    columnDefs: [
      {targets: [4, 6], type: 'num'},
      {targets: '_all', orderable: true}
    ],
    paging: false,
    responsive: false,
    dom: "<'px-6 pb-4 text-sm text-gray-700'>t",
    language: {
      info: ''
    }
  });

  $('#termFilter, #schoolFilter, #dayFilter').on('change', function () {
    dataTable.ajax.reload();
  });
});
