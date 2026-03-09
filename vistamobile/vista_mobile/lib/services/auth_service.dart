import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';

class AuthService {
  static final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: [
      'email',
      'https://www.googleapis.com/auth/calendar.readonly',
    ],
  );

  static GoogleSignInAccount? currentUser;

  static Future<GoogleSignInAccount?> signIn() async {
    try {
      currentUser = await _googleSignIn.signIn();
      return currentUser;
    } catch (e) {
      debugPrint('Google Sign-In error: $e');
      return null;
    }
  }

  static Future<GoogleSignInAccount?> signInSilently() async {
    try {
      currentUser = await _googleSignIn.signInSilently();
      return currentUser;
    } catch (e) {
      debugPrint('Google silent sign-in error: $e');
      return null;
    }
  }

  static Future<void> signOut() async {
    await _googleSignIn.signOut();
    currentUser = null;
  }

  static Future<Map<String, String>?> getAuthHeaders() async {
    return await currentUser?.authHeaders;
  }
}
