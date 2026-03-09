import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/auth_service.dart';
import '../services/calendar_service.dart';
import '../services/database_service.dart';
import 'login_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedTab = 0;
  List<CalendarEvent> _calendarEvents = [];
  List<TodoItem> _todos = [];
  bool _isLoading = true;
  bool _isDarkMode = false;
  final _todoController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _todoController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    await Future.wait([_loadCalendarEvents(), _loadTodos()]);
    setState(() => _isLoading = false);
  }

  Future<void> _loadCalendarEvents() async {
    final events = await CalendarService.getUpcomingEvents();
    if (mounted) setState(() => _calendarEvents = events);
  }

  Future<void> _loadTodos() async {
    final user = AuthService.currentUser;
    if (user == null) return;
    final todos = await DatabaseService.getTasks(user.id);
    if (mounted) setState(() => _todos = todos);
  }

  Future<void> _addTodo() async {
    final text = _todoController.text.trim();
    if (text.isEmpty) return;
    final user = AuthService.currentUser;
    if (user == null) return;

    final updated = List<TodoItem>.from(_todos)
      ..add(TodoItem(title: text));
    await DatabaseService.updateTasks(user.id, updated);
    _todoController.clear();
    await _loadTodos();
  }

  Future<void> _toggleTodo(TodoItem todo) async {
    final user = AuthService.currentUser;
    if (user == null) return;
    final index = _todos.indexOf(todo);
    if (index == -1) return;
    final updated = List<TodoItem>.from(_todos);
    updated[index] = TodoItem(title: todo.title, isCompleted: !todo.isCompleted);
    await DatabaseService.updateTasks(user.id, updated);
    await _loadTodos();
  }

  Future<void> _deleteTodo(TodoItem todo) async {
    final user = AuthService.currentUser;
    if (user == null) return;
    final updated = List<TodoItem>.from(_todos)..remove(todo);
    await DatabaseService.updateTasks(user.id, updated);
    await _loadTodos();
  }

  Future<void> _signOut() async {
    await AuthService.signOut();
    if (mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
      );
    }
  }

  // --- Theme colors ---
  Color get _bg => _isDarkMode
      ? const Color(0xFF0D0D0F)
      : const Color(0xFFF5F3F0);
  Color get _text => _isDarkMode
      ? const Color(0xFFF0EDE8)
      : const Color(0xFF1A1A1A);
  Color get _subtext => _isDarkMode
      ? const Color(0xFF8A8A8E)
      : const Color(0xFF7A7A7E);
  Color get _glassBg => _isDarkMode
      ? Colors.white.withValues(alpha: 0.06)
      : Colors.white.withValues(alpha: 0.55);
  Color get _glassBorder => _isDarkMode
      ? Colors.white.withValues(alpha: 0.10)
      : Colors.white.withValues(alpha: 0.80);
  Color get _accent => _isDarkMode
      ? const Color(0xFF7AD4E0)
      : const Color(0xFF58B2C0);

  Widget _glassContainer({required Widget child, EdgeInsets? padding, EdgeInsets? margin}) {
    return Container(
      margin: margin,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
          child: Container(
            padding: padding ?? const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: _glassBg,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: _glassBorder, width: 0.5),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: _isDarkMode ? 0.3 : 0.04),
                  blurRadius: 20,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: child,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = AuthService.currentUser;

    return Scaffold(
      backgroundColor: _bg,
      body: Stack(
        children: [
          // Gradient orbs for depth
          Positioned(
            top: -80,
            right: -60,
            child: Container(
              width: 250,
              height: 250,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: _isDarkMode
                      ? [const Color(0xFF58B2C0).withValues(alpha: 0.15), Colors.transparent]
                      : [const Color(0xFF7AD4E0).withValues(alpha: 0.25), Colors.transparent],
                ),
              ),
            ),
          ),
          Positioned(
            bottom: 100,
            left: -80,
            child: Container(
              width: 200,
              height: 200,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: _isDarkMode
                      ? [const Color(0xFF5A8F7B).withValues(alpha: 0.10), Colors.transparent]
                      : [const Color(0xFFA8D5BA).withValues(alpha: 0.20), Colors.transparent],
                ),
              ),
            ),
          ),
          // Main content
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildHeader(),
                  const SizedBox(height: 4),
                  Text(
                    'Your upcoming week',
                    style: TextStyle(fontSize: 14, color: _subtext, letterSpacing: 0.3),
                  ),
                  const SizedBox(height: 16),
                  _buildUserRow(user),
                  const SizedBox(height: 20),
                  _buildTabs(),
                  const SizedBox(height: 16),
                  Expanded(
                    child: _isLoading
                        ? Center(child: CircularProgressIndicator(color: _accent, strokeWidth: 2))
                        : _selectedTab == 0
                            ? _buildCalendarView()
                            : _buildTodoView(),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        const Text('🪶', style: TextStyle(fontSize: 28)),
        const SizedBox(width: 8),
        Text(
          'Vista',
          style: TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w700,
            color: _text,
            letterSpacing: -0.5,
          ),
        ),
        const Spacer(),
        GestureDetector(
          onTap: () => setState(() => _isDarkMode = !_isDarkMode),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
              child: Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _glassBg,
                  border: Border.all(color: _glassBorder, width: 0.5),
                ),
                child: Icon(
                  _isDarkMode ? Icons.dark_mode_rounded : Icons.light_mode_rounded,
                  size: 18,
                  color: _accent,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildUserRow(dynamic user) {
    return _glassContainer(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: _accent.withValues(alpha: 0.4), width: 2),
            ),
            child: CircleAvatar(
              radius: 20,
              backgroundImage: user?.photoUrl != null
                  ? NetworkImage(user!.photoUrl!)
                  : null,
              backgroundColor: _glassBg,
              child: user?.photoUrl == null
                  ? Icon(Icons.person_rounded, color: _subtext, size: 20)
                  : null,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              user?.displayName ?? 'User',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w600,
                color: _text,
              ),
            ),
          ),
          GestureDetector(
            onTap: _signOut,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                color: _isDarkMode
                    ? Colors.white.withValues(alpha: 0.08)
                    : Colors.black.withValues(alpha: 0.05),
              ),
              child: Text(
                'Sign out',
                style: TextStyle(fontSize: 12, color: _subtext, fontWeight: FontWeight.w500),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTabs() {
    return Center(
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
          child: Container(
            padding: const EdgeInsets.all(3),
            decoration: BoxDecoration(
              color: _glassBg,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: _glassBorder, width: 0.5),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _tabButton('Calendar', 0),
                _tabButton('To-Do', 1),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _tabButton(String text, int index) {
    final isSelected = _selectedTab == index;
    return GestureDetector(
      onTap: () => setState(() => _selectedTab = index),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? _accent : Colors.transparent,
          borderRadius: BorderRadius.circular(22),
        ),
        child: Text(
          text,
          style: TextStyle(
            fontSize: 14,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
            color: isSelected ? Colors.white : _subtext,
          ),
        ),
      ),
    );
  }

  Widget _buildCalendarView() {
    if (_calendarEvents.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.calendar_today_rounded, size: 40, color: _subtext.withValues(alpha: 0.4)),
            const SizedBox(height: 12),
            Text(
              'No upcoming events',
              style: TextStyle(color: _subtext, fontSize: 15),
            ),
          ],
        ),
      );
    }

    return ListView.separated(
      itemCount: _calendarEvents.length,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (context, index) => _eventCard(_calendarEvents[index]),
    );
  }

  Widget _eventCard(CalendarEvent event) {
    final dayStr = DateFormat('dd').format(event.date);
    final monthStr = DateFormat('MMM').format(event.date).toUpperCase();

    return _glassContainer(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Container(
            width: 52,
            padding: const EdgeInsets.symmetric(vertical: 6),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              color: _accent.withValues(alpha: 0.12),
            ),
            child: Column(
              children: [
                Text(
                  dayStr,
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    color: _accent,
                  ),
                ),
                Text(
                  monthStr,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: _accent.withValues(alpha: 0.7),
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          Container(
            width: 1,
            height: 36,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  _glassBorder.withValues(alpha: 0.0),
                  _glassBorder,
                  _glassBorder.withValues(alpha: 0.0),
                ],
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              event.title,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w500,
                color: _text,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTodoView() {
    return Column(
      children: [
        _glassContainer(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _todoController,
                  style: TextStyle(color: _text, fontSize: 15),
                  decoration: InputDecoration(
                    hintText: 'Add a new task...',
                    hintStyle: TextStyle(color: _subtext.withValues(alpha: 0.6)),
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14),
                  ),
                  onSubmitted: (_) => _addTodo(),
                ),
              ),
              GestureDetector(
                onTap: _addTodo,
                child: Container(
                  margin: const EdgeInsets.only(right: 8),
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: _accent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(Icons.add_rounded, color: _accent, size: 20),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Expanded(
          child: _todos.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.check_circle_outline_rounded, size: 40, color: _subtext.withValues(alpha: 0.4)),
                      const SizedBox(height: 12),
                      Text(
                        'No tasks yet',
                        style: TextStyle(color: _subtext, fontSize: 15),
                      ),
                    ],
                  ),
                )
              : ListView.separated(
                  itemCount: _todos.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, index) => _todoCard(_todos[index]),
                ),
        ),
      ],
    );
  }

  Widget _todoCard(TodoItem todo) {
    return Dismissible(
      key: Key('todo-${todo.title}-${todo.isCompleted}'),
      direction: DismissDirection.endToStart,
      onDismissed: (_) => _deleteTodo(todo),
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          gradient: LinearGradient(
            colors: [Colors.red.withValues(alpha: 0.0), Colors.red.withValues(alpha: 0.15)],
          ),
        ),
        child: Icon(Icons.delete_rounded, color: Colors.red[300], size: 22),
      ),
      child: GestureDetector(
        onTap: () => _toggleTodo(todo),
        child: _glassContainer(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          child: Row(
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 24,
                height: 24,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: todo.isCompleted ? _accent : Colors.transparent,
                  border: Border.all(
                    color: todo.isCompleted ? _accent : _subtext.withValues(alpha: 0.3),
                    width: 1.5,
                  ),
                ),
                child: todo.isCompleted
                    ? const Icon(Icons.check_rounded, color: Colors.white, size: 16)
                    : null,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  todo.title,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w500,
                    color: todo.isCompleted
                        ? _subtext.withValues(alpha: 0.5)
                        : _text,
                    decoration: todo.isCompleted
                        ? TextDecoration.lineThrough
                        : TextDecoration.none,
                    decorationColor: _subtext.withValues(alpha: 0.4),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
