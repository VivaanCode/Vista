import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../config.dart';

class TodoItem {
  final String title;
  final bool isCompleted;

  TodoItem({
    required this.title,
    this.isCompleted = false,
  });

  Map<String, dynamic> toJson() => {
        'title': title,
        'isCompleted': isCompleted,
      };

  factory TodoItem.fromJson(Map<String, dynamic> json) => TodoItem(
        title: json['title'] as String,
        isCompleted: json['isCompleted'] as bool? ?? false,
      );
}

class DatabaseService {
  static Future<bool> addSub(String sub) async {
    try {
      final response = await http.post(
        Uri.parse('${AppConfig.serverUrl}/addSub'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'sub': sub}),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Error adding sub: $e');
      return false;
    }
  }

  static Future<List<TodoItem>> getTasks(String sub) async {
    try {
      debugPrint('getTasks: calling ${AppConfig.serverUrl}/getTasks for sub=$sub');
      final response = await http.post(
        Uri.parse('${AppConfig.serverUrl}/getTasks'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'sub': sub}),
      );
      debugPrint('getTasks: status=${response.statusCode} body=${response.body}');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final tasks = data['tasks'];
        if (tasks == null) return [];
        return (tasks as List)
            .map((t) => TodoItem.fromJson(t as Map<String, dynamic>))
            .toList();
      }
      return [];
    } catch (e) {
      debugPrint('Error getting tasks: $e');
      return [];
    }
  }

  static Future<bool> updateTasks(String sub, List<TodoItem> tasks) async {
    try {
      debugPrint('updateTasks: calling ${AppConfig.serverUrl}/updateTasks for sub=$sub with ${tasks.length} tasks');
      final response = await http.post(
        Uri.parse('${AppConfig.serverUrl}/updateTasks'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'sub': sub,
          'tasks': tasks.map((t) => t.toJson()).toList(),
        }),
      );
      debugPrint('updateTasks: status=${response.statusCode} body=${response.body}');
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Error updating tasks: $e');
      return false;
    }
  }
}
