import 'package:googleapis/calendar/v3.dart' as gcal;
import 'package:http/http.dart' as http;
import 'auth_service.dart';

class _AuthenticatedClient extends http.BaseClient {
  final Map<String, String> _headers;
  final http.Client _inner = http.Client();

  _AuthenticatedClient(this._headers);

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    request.headers.addAll(_headers);
    return _inner.send(request);
  }
}

class CalendarEvent {
  final String title;
  final DateTime date;

  CalendarEvent({required this.title, required this.date});
}

class CalendarService {
  static Future<List<CalendarEvent>> getUpcomingEvents() async {
    try {
      final headers = await AuthService.getAuthHeaders();
      if (headers == null) return [];

      final client = _AuthenticatedClient(headers);
      final calendarApi = gcal.CalendarApi(client);

      final now = DateTime.now();
      final oneWeekLater = now.add(const Duration(days: 7));

      final events = await calendarApi.events.list(
        'primary',
        timeMin: now.toUtc(),
        timeMax: oneWeekLater.toUtc(),
        orderBy: 'startTime',
        singleEvents: true,
        maxResults: 20,
      );

      return (events.items ?? []).map((event) {
        final start = event.start?.dateTime ?? event.start?.date ?? now;
        return CalendarEvent(
          title: event.summary ?? 'No title',
          date: start,
        );
      }).toList();
    } catch (e) {
      return [];
    }
  }
}
