class Student {
  final int? id;
  final String admissionNo;
  final String fullName;
  final String? className;
  final String? guardianName;
  final String? guardianPhone;

  Student({
    this.id,
    required this.admissionNo,
    required this.fullName,
    this.className,
    this.guardianName,
    this.guardianPhone,
  });

  Map<String, Object?> toMap() => {
        'id': id,
        'admission_no': admissionNo,
        'full_name': fullName,
        'class_name': className,
        'guardian_name': guardianName,
        'guardian_phone': guardianPhone,
        'created_at': DateTime.now().toIso8601String(),
      };

  factory Student.fromMap(Map<String, Object?> m) => Student(
        id: m['id'] as int?,
        admissionNo: (m['admission_no'] ?? '') as String,
        fullName: (m['full_name'] ?? '') as String,
        className: m['class_name'] as String?,
        guardianName: m['guardian_name'] as String?,
        guardianPhone: m['guardian_phone'] as String?,
      );
}

class Teacher {
  final int? id;
  final String fullName;
  final String? phone;
  final String? subject;

  Teacher({this.id, required this.fullName, this.phone, this.subject});

  Map<String, Object?> toMap() => {
        'id': id,
        'full_name': fullName,
        'phone': phone,
        'subject': subject,
        'created_at': DateTime.now().toIso8601String(),
      };

  factory Teacher.fromMap(Map<String, Object?> m) => Teacher(
        id: m['id'] as int?,
        fullName: (m['full_name'] ?? '') as String,
        phone: m['phone'] as String?,
        subject: m['subject'] as String?,
      );
}

class FeeRecord {
  final int? id;
  final int studentId;
  final String term;
  final double amount;
  final double paid;

  FeeRecord({
    this.id,
    required this.studentId,
    required this.term,
    required this.amount,
    this.paid = 0,
  });

  double get balance => amount - paid;

  Map<String, Object?> toMap() => {
        'id': id,
        'student_id': studentId,
        'term': term,
        'amount': amount,
        'paid': paid,
        'created_at': DateTime.now().toIso8601String(),
      };

  factory FeeRecord.fromMap(Map<String, Object?> m) => FeeRecord(
        id: m['id'] as int?,
        studentId: (m['student_id'] ?? 0) as int,
        term: (m['term'] ?? '') as String,
        amount: ((m['amount'] ?? 0) as num).toDouble(),
        paid: ((m['paid'] ?? 0) as num).toDouble(),
      );
}
