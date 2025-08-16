function printDiv(divName) {
    var printContents = document.getElementById(divName).innerHTML;
    var printWindow = window.open('', '_blank');

    printWindow.document.write('<html><head><title>Print</title>');
    printWindow.document.write('<style>');
    printWindow.document.write('body { font-size: 12pt; margin-top: 20px; font-family: sans-serif; } ');
    printWindow.document.write('h2 { text-align: center; font-size: 20pt; }');
    printWindow.document.write('table { width: 80%; margin: 0 auto; border-collapse: collapse; } ');
    printWindow.document.write('th, td { border: 1px solid #ccc; padding: 8px; text-align: left; } ');
    printWindow.document.write('thead { background-color: #f5f5f5; }');
    printWindow.document.write('</style></head><body>');
    printWindow.document.write(printContents);
    printWindow.document.write('</body></html>');

    printWindow.document.close();
    setTimeout(function () {
        printWindow.print();
        printWindow.close();
    }, 250);
}
