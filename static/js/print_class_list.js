function printDiv(divName) {
    var printContents = document.getElementById(divName).innerHTML;
    var productTitle = document.querySelector('h2.text-3xl.font-bold.text-blue-700');
    var titleText = productTitle ? productTitle.textContent : '';
    var printWindow = window.open('', '_blank');

    printWindow.document.write('<html><head><title>Print</title>');
    printWindow.document.write('<style>');
    printWindow.document.write('body { font-size: 12pt; margin-top: 20px; font-family: sans-serif; } ');
    printWindow.document.write('h2 { text-align: center; font-size: 20pt; margin-bottom: 20px; }');
    printWindow.document.write('table { width: 80%; margin: 0 auto; border-collapse: collapse; } ');
    printWindow.document.write('th, td { border: 1px solid #ccc; padding: 8px; text-align: left; } ');
    printWindow.document.write('thead { background-color: #f5f5f5; }');
    printWindow.document.write('</style></head><body>');
    if (titleText) {
        printWindow.document.write('<h2>' + titleText + '</h2>');
    }
    printWindow.document.write(printContents);
    printWindow.document.write('</body></html>');

    printWindow.document.close();
    setTimeout(function () {
        printWindow.print();
        printWindow.close();
    }, 250);
}
