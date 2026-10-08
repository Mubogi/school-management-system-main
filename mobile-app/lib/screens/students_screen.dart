import 'package:flutter/material.dart';
import '../data/models.dart';
import '../data/repository.dart';

class StudentsScreen extends StatefulWidget {
  const StudentsScreen({super.key});

  @override
  State<StudentsScreen> createState() => _StudentsScreenState();
}

class _StudentsScreenState extends State<StudentsScreen> {
  final _search = TextEditingController();
  List<Student> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
    _search.addListener(_load);
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final items = await Repository.instance.students(query: _search.text);
    if (mounted) {
      setState(() {
        _items = items;
        _loading = false;
      });
    }
  }

  Future<void> _add() async {
    final result = await showModalBottomSheet<Student>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _StudentForm(),
    );
    if (result != null) {
      await Repository.instance.addStudent(result);
      await _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Students')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _add,
        icon: const Icon(Icons.add),
        label: const Text('Add student'),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _search,
              decoration: const InputDecoration(
                hintText: 'Search name, admission no or class',
                prefixIcon: Icon(Icons.search),
              ),
            ),
          ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _items.isEmpty
                    ? const _Empty(
                        icon: Icons.people_outline,
                        text: 'No students yet. Tap "Add student".',
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.only(bottom: 90),
                        itemCount: _items.length,
                        itemBuilder: (_, i) {
                          final s = _items[i];
                          return Card(
                            child: ListTile(
                              leading: const CircleAvatar(
                                  child: Icon(Icons.person)),
                              title: Text(s.fullName),
                              subtitle: Text([
                                if (s.admissionNo.isNotEmpty)
                                  'No: ${s.admissionNo}',
                                if (s.className != null &&
                                    s.className!.isNotEmpty)
                                  s.className!,
                                if (s.guardianName != null &&
                                    s.guardianName!.isNotEmpty)
                                  'Guardian: ${s.guardianName}',
                              ].join('  •  ')),
                              trailing: IconButton(
                                icon: const Icon(Icons.delete_outline),
                                onPressed: () async {
                                  await Repository.instance
                                      .deleteStudent(s.id!);
                                  await _load();
                                },
                              ),
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}

class _StudentForm extends StatefulWidget {
  const _StudentForm();

  @override
  State<_StudentForm> createState() => _StudentFormState();
}

class _StudentFormState extends State<_StudentForm> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _adm = TextEditingController();
  final _cls = TextEditingController();
  final _guardian = TextEditingController();
  final _phone = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: Form(
        key: _form,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text('New student',
                  style:
                      TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              TextFormField(
                controller: _name,
                decoration: const InputDecoration(labelText: 'Full name *'),
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Required' : null,
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _adm,
                decoration:
                    const InputDecoration(labelText: 'Admission number'),
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _cls,
                decoration: const InputDecoration(labelText: 'Class'),
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _guardian,
                decoration: const InputDecoration(labelText: 'Guardian name'),
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                decoration:
                    const InputDecoration(labelText: 'Guardian phone'),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () {
                  if (_form.currentState!.validate()) {
                    Navigator.of(context).pop(Student(
                      fullName: _name.text.trim(),
                      admissionNo: _adm.text.trim(),
                      className: _cls.text.trim(),
                      guardianName: _guardian.text.trim(),
                      guardianPhone: _phone.text.trim(),
                    ));
                  }
                },
                child: const Text('Save student'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  final IconData icon;
  final String text;
  const _Empty({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 56, color: Colors.black26),
            const SizedBox(height: 12),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(text,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.black54)),
            ),
          ],
        ),
      );
}
