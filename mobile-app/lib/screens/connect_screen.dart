import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../widgets/app_theme.dart';

/// QR helper. Renders a scannable code for a connection address or any text,
/// entirely on the device (no library download, no network).
class ConnectScreen extends StatefulWidget {
  const ConnectScreen({super.key});

  @override
  State<ConnectScreen> createState() => _ConnectScreenState();
}

class _ConnectScreenState extends State<ConnectScreen> {
  final _text = TextEditingController(text: 'http://192.168.1.10:8000/');

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final value = _text.text.trim();
    return Scaffold(
      appBar: AppBar(title: const Text('Connect / QR')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Show this code for another phone or computer to scan. Point it at '
            'the PC edition of the school system on your local network, or type '
            'any text you want to share as a QR code.',
            style: TextStyle(color: Colors.black54),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _text,
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(
              labelText: 'Text or address to encode',
              prefixIcon: Icon(Icons.link),
            ),
          ),
          const SizedBox(height: 24),
          Center(
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.08),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  )
                ],
              ),
              child: value.isEmpty
                  ? const SizedBox(
                      width: 240,
                      height: 240,
                      child: Center(child: Text('Enter some text')),
                    )
                  : QrImageView(
                      data: value,
                      version: QrVersions.auto,
                      size: 240,
                      backgroundColor: Colors.white,
                      foregroundColor: BrandColors.blueDark,
                    ),
            ),
          ),
          const SizedBox(height: 20),
          Center(
            child: OutlinedButton.icon(
              onPressed: value.isEmpty
                  ? null
                  : () async {
                      await Clipboard.setData(ClipboardData(text: value));
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Copied to clipboard')),
                        );
                      }
                    },
              icon: const Icon(Icons.copy),
              label: const Text('Copy text'),
            ),
          ),
        ],
      ),
    );
  }
}
