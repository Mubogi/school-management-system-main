import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:pdf/pdf.dart';
import 'package:printing/printing.dart';
import '../data/repository.dart';

/// Reports are rendered to a real PDF natively (no browser, no server) and can
/// be printed or shared with any app on the phone.
class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key});

  Future<void> _studentsPdf(BuildContext context) async {
    final students = await Repository.instance.students();
    final doc = pw.Document();
    doc.addPage(pw.MultiPage(
      pageFormat: PdfPageFormat.a4,
      build: (_) => [
        pw.Header(
          level: 0,
          child: pw.Text('JD Hub School - Student Register',
              style: pw.TextStyle(
                  fontSize: 18, fontWeight: pw.FontWeight.bold)),
        ),
        pw.Text('Generated: ${DateFormat.yMMMd().add_jm().format(DateTime.now())}'),
        pw.SizedBox(height: 12),
        pw.TableHelper.fromTextArray(
          headers: ['#', 'Name', 'Admission No', 'Class', 'Guardian', 'Phone'],
          data: [
            for (var i = 0; i < students.length; i++)
              [
                '${i + 1}',
                students[i].fullName,
                students[i].admissionNo,
                students[i].className ?? '',
                students[i].guardianName ?? '',
                students[i].guardianPhone ?? '',
              ]
          ],
        ),
      ],
    ));
    await Printing.layoutPdf(
      name: 'student-register.pdf',
      onLayout: (_) => doc.save(),
    );
  }

  Future<void> _feesPdf(BuildContext context) async {
    final rows = await Repository.instance.feeRows();
    final money = NumberFormat('#,##0');
    final doc = pw.Document();
    doc.addPage(pw.MultiPage(
      pageFormat: PdfPageFormat.a4,
      build: (_) => [
        pw.Header(
          level: 0,
          child: pw.Text('JD Hub School - Fees Report',
              style: pw.TextStyle(
                  fontSize: 18, fontWeight: pw.FontWeight.bold)),
        ),
        pw.Text('Generated: ${DateFormat.yMMMd().add_jm().format(DateTime.now())}'),
        pw.SizedBox(height: 12),
        pw.TableHelper.fromTextArray(
          headers: ['Student', 'Term', 'Amount', 'Paid', 'Balance'],
          data: [
            for (final r in rows)
              [
                '${r['student']}',
                '${r['term']}',
                money.format(r['amount']),
                money.format(r['paid']),
                money.format(r['balance']),
              ]
          ],
        ),
      ],
    ));
    await Printing.layoutPdf(
      name: 'fees-report.pdf',
      onLayout: (_) => doc.save(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Reports & PDFs')),
      body: ListView(
        children: [
          _tile(context, Icons.people, 'Student register (PDF)',
              'List every student with guardian details', _studentsPdf),
          _tile(context, Icons.payments, 'Fees report (PDF)',
              'Amounts due, paid and outstanding balances', _feesPdf),
        ],
      ),
    );
  }

  Widget _tile(BuildContext context, IconData icon, String title, String sub,
      Future<void> Function(BuildContext) onTap) {
    return Card(
      child: ListTile(
        leading: Icon(icon),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(sub),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => onTap(context),
      ),
    );
  }
}
