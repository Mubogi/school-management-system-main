import 'package:flutter/material.dart';
import '../data/repository.dart';
import '../widgets/app_theme.dart';
import 'students_screen.dart';
import 'teachers_screen.dart';
import 'fees_screen.dart';
import 'reports_screen.dart';
import 'connect_screen.dart';

/// Dashboard. Everything is local, so there is no login or network step - the
/// app is ready the moment it opens.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Map<String, int> _summary = const {'students': 0, 'teachers': 0, 'fees': 0};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final s = await Repository.instance.summary();
    if (mounted) setState(() => _summary = s);
  }

  void _open(Widget screen) {
    Navigator.of(context)
        .push(MaterialPageRoute(builder: (_) => screen))
        .then((_) => _load());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('JD Hub School'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.only(bottom: 24),
          children: [
            _header(context),
            _statRow(context),
            const SizedBox(height: 8),
            _navCard(context, Icons.people, 'Students',
                '${_summary['students']} on record', const StudentsScreen()),
            _navCard(context, Icons.school, 'Teachers',
                '${_summary['teachers']} on record', const TeachersScreen()),
            _navCard(context, Icons.payments, 'Fees',
                '${_summary['fees']} records', const FeesScreen()),
            _navCard(context, Icons.picture_as_pdf, 'Reports & PDFs',
                'Print or share a PDF', const ReportsScreen()),
            _navCard(context, Icons.qr_code_2, 'Connect / QR',
                'Open the school system on a computer', const ConnectScreen()),
          ],
        ),
      ),
    );
  }

  Widget _header(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [BrandColors.blue, BrandColors.blueDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Image.asset('assets/logo.png', height: 42),
              const SizedBox(width: 12),
              const Expanded(
                child: Text(
                  'School Management System',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text('Offline edition - works without internet',
              style: TextStyle(color: Colors.white70, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _statRow(BuildContext context) {
    Widget tile(String label, int value, IconData icon) => Expanded(
          child: Card(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
              child: Column(
                children: [
                  Icon(icon, color: BrandColors.blue),
                  const SizedBox(height: 8),
                  Text('$value',
                      style: const TextStyle(
                          fontSize: 22, fontWeight: FontWeight.bold)),
                  Text(label,
                      style: const TextStyle(
                          fontSize: 12, color: Colors.black54)),
                ],
              ),
            ),
          ),
        );
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(
        children: [
          tile('Students', _summary['students'] ?? 0, Icons.people),
          tile('Teachers', _summary['teachers'] ?? 0, Icons.school),
          tile('Fees', _summary['fees'] ?? 0, Icons.payments),
        ],
      ),
    );
  }

  Widget _navCard(BuildContext context, IconData icon, String title,
      String subtitle, Widget screen) {
    return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: BrandColors.blue.withOpacity(0.1),
          child: Icon(icon, color: BrandColors.blue),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => _open(screen),
      ),
    );
  }
}
