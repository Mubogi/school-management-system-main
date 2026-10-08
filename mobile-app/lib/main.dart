import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'widgets/app_theme.dart';

void main() {
  runApp(const JDHubSchoolApp());
}

/// Standalone offline edition. There is no embedded interpreter and no server:
/// the app reads and writes a local SQLite file, so it opens instantly and
/// cannot fail to "start".
class JDHubSchoolApp extends StatelessWidget {
  const JDHubSchoolApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'JD Hub School',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      home: const HomeScreen(),
    );
  }
}
