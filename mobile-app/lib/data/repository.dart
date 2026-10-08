import 'package:sqflite/sqflite.dart';
import 'database.dart';
import 'models.dart';

/// All reads and writes go through here. Every method is async and hits the
/// local SQLite file, so the app never needs a network connection.
class Repository {
  Repository._();
  static final Repository instance = Repository._();

  Future<Database> get _db => AppDatabase.instance.database;

  // --- Students -------------------------------------------------------------
  Future<List<Student>> students({String query = ''}) async {
    final db = await _db;
    final rows = query.trim().isEmpty
        ? await db.query('students', orderBy: 'full_name COLLATE NOCASE')
        : await db.query(
            'students',
            where: 'full_name LIKE ? OR admission_no LIKE ? OR class_name LIKE ?',
            whereArgs: ['%$query%', '%$query%', '%$query%'],
            orderBy: 'full_name COLLATE NOCASE',
          );
    return rows.map(Student.fromMap).toList();
  }

  Future<int> addStudent(Student s) async {
    final db = await _db;
    return db.insert('students', s.toMap()..remove('id'));
  }

  Future<void> deleteStudent(int id) async {
    final db = await _db;
    await db.delete('students', where: 'id = ?', whereArgs: [id]);
  }

  // --- Teachers -------------------------------------------------------------
  Future<List<Teacher>> teachers({String query = ''}) async {
    final db = await _db;
    final rows = query.trim().isEmpty
        ? await db.query('teachers', orderBy: 'full_name COLLATE NOCASE')
        : await db.query(
            'teachers',
            where: 'full_name LIKE ? OR subject LIKE ?',
            whereArgs: ['%$query%', '%$query%'],
            orderBy: 'full_name COLLATE NOCASE',
          );
    return rows.map(Teacher.fromMap).toList();
  }

  Future<int> addTeacher(Teacher t) async {
    final db = await _db;
    return db.insert('teachers', t.toMap()..remove('id'));
  }

  Future<void> deleteTeacher(int id) async {
    final db = await _db;
    await db.delete('teachers', where: 'id = ?', whereArgs: [id]);
  }

  // --- Fees -----------------------------------------------------------------
  Future<List<Map<String, Object?>>> feeRows() async {
    final db = await _db;
    return db.rawQuery('''
      SELECT f.id, s.full_name AS student, f.term, f.amount, f.paid,
             (f.amount - f.paid) AS balance
      FROM fees f JOIN students s ON s.id = f.student_id
      ORDER BY s.full_name COLLATE NOCASE
    ''');
  }

  Future<int> addFee(FeeRecord f) async {
    final db = await _db;
    return db.insert('fees', f.toMap()..remove('id'));
  }

  Future<void> deleteFee(int id) async {
    final db = await _db;
    await db.delete('fees', where: 'id = ?', whereArgs: [id]);
  }

  // --- Dashboard ------------------------------------------------------------
  Future<Map<String, int>> summary() async {
    final db = await _db;
    Future<int> c(String sql) async =>
        (Sqflite.firstIntValue(await db.rawQuery(sql)) ?? 0);
    return {
      'students': await c('SELECT COUNT(*) FROM students'),
      'teachers': await c('SELECT COUNT(*) FROM teachers'),
      'fees': await c('SELECT COUNT(*) FROM fees'),
    };
  }
}
