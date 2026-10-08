import 'package:flutter/material.dart';
import '../data/models.dart';
import '../data/repository.dart';

class TeachersScreen extends StatefulWidget {
  const TeachersScreen({super.key});

  @override
  State<TeachersScreen> createState() => _TeachersScreenState();
}

class _TeachersScreenState extends State<TeachersScreen> {
  List<Teacher> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final items = await Repository.instance.teachers();
    if (mounted) {
      setState(() {
        _items = items;
        _loading = false;
      });
    }
  }

  Future<void> _add() async {
    final result = await showModalBottomSheet<Teacher>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _TeacherForm(),
    );
    if (result != null) {
      await Repository.instance.addTeacher(result);
      await _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Teachers')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _add,
        icon: const Icon(Icons.add),
        label: const Text('Add teacher'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? const Center(
                  child: Text('No teachers yet. Tap "Add teacher".',
                      style: TextStyle(color: Colors.black54)))
              : ListView.builder(
                  padding: const EdgeInsets.only(bottom: 90),
                  itemCount: _items.length,
                  itemBuilder: (_, i) {
                    final t = _items[i];
                    return Card(
                      child: ListTile(
                        leading: const CircleAvatar(child: Icon(Icons.school)),
                        title: Text(t.fullName),
                        subtitle: Text([
                          if (t.subject != null && t.subject!.isNotEmpty)
                            t.subject!,
                          if (t.phone != null && t.phone!.isNotEmpty) t.phone!,
                        ].join('  •  ')),
                        trailing: IconButton(
                          icon: const Icon(Icons.delete_outline),
                          onPressed: () async {
                            await Repository.instance.deleteTeacher(t.id!);
                            await _load();
                          },
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}

class _TeacherForm extends StatefulWidget {
  const _TeacherForm();

  @override
  State<_TeacherForm> createState() => _TeacherFormState();
}

class _TeacherFormState extends State<_TeacherForm> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _subject = TextEditingController();
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
              const Text('New teacher',
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
                controller: _subject,
                decoration: const InputDecoration(labelText: 'Subject'),
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(labelText: 'Phone'),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () {
                  if (_form.currentState!.validate()) {
                    Navigator.of(context).pop(Teacher(
                      fullName: _name.text.trim(),
                      subject: _subject.text.trim(),
                      phone: _phone.text.trim(),
                    ));
                  }
                },
                child: const Text('Save teacher'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
