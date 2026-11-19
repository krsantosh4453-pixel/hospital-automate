import 'dart:async';

import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../core/localization/l10n.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_typography.dart';
import 'hms_button.dart';
import 'hms_card.dart';
import 'hms_search_field.dart';
import 'states.dart';

/// Search-then-pick for one record (a patient to bill or order for). The
/// server does the matching; nothing is chosen until the person taps a row,
/// so two people with the same name are never picked by name alone.
class RecordPicker<T> extends StatefulWidget {
  const RecordPicker({
    super.key,
    required this.search,
    required this.title,
    required this.subtitle,
    required this.onSelected,
    required this.hint,
    this.selected,
    this.minChars = 3,
    this.enabled = true,
  });

  final Future<List<T>> Function(String query) search;
  final String Function(T item) title;
  final String Function(T item) subtitle;
  final ValueChanged<T?> onSelected;
  final String hint;
  final T? selected;

  /// The server refuses shorter lookups (patients/lookup/ needs three).
  final int minChars;
  final bool enabled;

  @override
  State<RecordPicker<T>> createState() => _RecordPickerState<T>();
}

class _RecordPickerState<T> extends State<RecordPicker<T>> {
  static const _debounce = Duration(milliseconds: 350);
  Timer? _timer;
  int _latest = 0;
  List<T>? _results;
  Object? _error;
  bool _searching = false;
  String _query = '';

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _changed(String value) {
    _query = value.trim();
    _timer?.cancel();
    if (_query.length < widget.minChars) {
      setState(() {
        _results = null;
        _error = null;
      });
      return;
    }
    _timer = Timer(_debounce, _run);
  }

  Future<void> _run() async {
    if (_query.length < widget.minChars) return;
    final request = ++_latest;
    setState(() {
      _searching = true;
      _error = null;
    });
    try {
      final found = await widget.search(_query);
      if (!mounted || request != _latest) return;
      setState(() => _results = found);
    } catch (error) {
      if (!mounted || request != _latest) return;
      setState(() => _error = error);
    } finally {
      if (mounted && request == _latest) setState(() => _searching = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.l10n;
    final chosen = widget.selected;
    if (chosen != null) {
      return HmsCard(
        child: ListTile(
          key: const Key('picked-record'),
          leading: const Icon(LucideIcons.userRoundCheck),
          title: Text(widget.title(chosen), style: AppTypography.body()),
          subtitle: Text(widget.subtitle(chosen)),
          trailing: widget.enabled
              ? HmsButton(
                  label: t.pickerChange,
                  variant: HmsButtonVariant.ghost,
                  surface: HmsSurface.card,
                  onPressed: () => widget.onSelected(null),
                )
              : null,
        ),
      );
    }
    final results = _results;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        HmsSearchField(
          key: const Key('record-picker-search'),
          hint: widget.hint,
          onChanged: _changed,
          onSubmitted: (_) => _run(),
        ),
        if (_searching) const LinearProgressIndicator(),
        const SizedBox(height: AppSpacing.x2),
        if (_query.isNotEmpty && _query.length < widget.minChars)
          Text(t.pickerTypeMore(widget.minChars), style: AppTypography.small())
        else if (_error != null)
          HmsErrorState(error: _error!, onRetry: _run)
        else if (results != null && results.isEmpty)
          HmsEmptyState(compact: true, title: t.noPatientsFound)
        else if (results != null)
          HmsCard(
            child: HmsDividedColumn(
              children: [
                for (final item in results)
                  ListTile(
                    title: Text(widget.title(item)),
                    subtitle: Text(widget.subtitle(item)),
                    onTap: widget.enabled
                        ? () => widget.onSelected(item)
                        : null,
                  ),
              ],
            ),
          ),
      ],
    );
  }
}
