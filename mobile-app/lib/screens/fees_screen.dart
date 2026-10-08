import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../data/models.dart';
import '../data/repository.dart';

class FeesScreen extends StatefulWidget {
  const FeesScreen({super.key});

  @override
  State<FeesScreen> createState() => _FeesScreenState();
}

class _FeesScreenState extends State<FeesScreen> {
  List<Map<String, Object?>> _rows = [];
  List<Student> _students = [];
  bool _loading = true;
  final _money = NumberFormat('#,##0');

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final rows = await Repository.instance.feeRows();
    final students = await Repository.instance.students();
    if (mounted) {
      setState(() {
        _rows = rows;
        _students = students;
        _loading = false;
      });
    }
  }

  Future<void> _add() async {
    if (_students.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Add a student first.')),
      );
      return;
    }
    final result = await showModalBottomSheet<FeeRecord>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _FeeForm(students: _students),
    );
    if (result != null) {
      await Repository.instance.addFee(result);
      await _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Fees')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _add,
        icon: const Icon(Icons.add),
        label: const Text('Add fee'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _rows.isEmpty
              ? const Center(
                  child: Text('No fee records yet. Tap "Add fee".',
                      style: TextStyle(color: Colors.black54)))
              : ListView.builder(
                  padding: const EdgeInsets.only(bottom: 90),
                  itemCount: _rows.length,
                  itemBuilder: (_, i) {
                    final r = _rows[i];
                    final balance = (r['balance'] as num).toDouble();
                    return Card(
                      child: ListTile(
                        leading: CircleAvatar(
                          backgroundColor: balance <= 0
                              ? Colors.green.shade100
                              : Colors.orange.shade100,
                          child: Icon(
                            balance <= 0 ? Icons.check : Icons.pending,
                            color: balance <= 0
                                ? Colors.green.shade800
                                : Colors.orange.shade800,
                          ),
                        ),
                        title: Text('${r['student']}'),
                        subtitle: Text(
                            '${r['term']}  •  paid ${_money.format(r['paid'])} of ${_money.format(r['amount'])}'),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text('Balance',
                                style: TextStyle(
                                    fontSize: 11, color: Colors.grey[600])),
                            Text(_money.format(balance),
                                style: const TextStyle(
                                    fontWeight: FontWeight.bold)),
                          ],
                        ),
                        onTap: () async {
                          await Repository.instance.deleteFee(r['id'] as int);
                          await _load();
                        },
                      ),
                    );
                  },
                ),
    );
  }
}

class _FeeForm extends StatefulWidget {
  final List<Student> students;
  const _FeeForm({required this.students});

  @override
  State<_FeeForm> createState() => _FeeFormState();
}

class _FeeFormState extends State<_FeeForm> {
  final _form = GlobalKey<FormState>();
  final _amount = TextEditingController();
  final _paid = TextEditingController(text: '0');
  final _term = TextEditingController(text: 'Term 1');
  int? _studentId;

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
              const Text('New fee record',
                  style:
                      TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              DropdownButtonFormField<int>(
                value: _studentId,
                decoration: const InputDecoration(labelText: 'Student *'),
                items: widget.students
                    .map((s) => DropdownMenuItem(
                          value: s.id,
                          child: Text(s.fullName),
                        ))
                    .toList(),
                onChanged: (v) => setState(() => _studentId = v),
                validator: (v) => v == null ? 'Required' : null,
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _term,
                decoration: const InputDecoration(labelText: 'Term'),
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _amount,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Amount due *'),
                validator: (v) => (double.tryParse(v ?? '') == null)
                    ? 'Enter a number'
                    : null,
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: _paid,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Amount paid'),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () {
                  if (_form.currentState!.validate()) {
                    Navigator.of(context).pop(FeeRecord(
                      studentId: _studentId!,
                      term: _term.text.trim(),
                      amount: double.parse(_amount.text.trim()),
                      paid: double.tryParse(_paid.text.trim()) ?? 0,
                    ));
                  }
                },
                child: const Text('Save fee'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
