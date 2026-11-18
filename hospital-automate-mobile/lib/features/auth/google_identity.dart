import 'package:google_sign_in/google_sign_in.dart';

/// Google's sign-in sheet, reduced to what the app needs: one ID token for
/// the backend's `auth/google/`, which checks it with Google. The token is
/// passed straight on and never stored.
abstract interface class GoogleIdentity {
  /// False on platforms or builds where Google sign-in cannot run; the
  /// button is then not shown.
  bool get isAvailable;

  /// Opens Google's account picker. Returns the ID token, or null when the
  /// person closed the picker. Throws [GoogleSignInFailure] otherwise.
  Future<String?> requestIdToken();
}

/// Why Google sign-in did not produce a token.
class GoogleSignInFailure implements Exception {
  const GoogleSignInFailure({required this.misconfigured});

  /// The app's Google client is not set up (e.g. this build's signing key
  /// is not registered in Google Cloud), as opposed to a passing failure.
  final bool misconfigured;
}

/// Which Google client the backend accepts tokens for (its
/// `GOOGLE_CLIENT_ID`). The same public Web client ID the web app uses;
/// override per deployment:
///
///     flutter run --dart-define=GOOGLE_SERVER_CLIENT_ID=<id>.apps.googleusercontent.com
abstract final class GoogleConfig {
  static const _override = String.fromEnvironment('GOOGLE_SERVER_CLIENT_ID');
  static const _webClientId =
      '119950053071-f93kl31rlntoo9jq35bgtc69rcqtrti5.apps.googleusercontent.com';

  static String get serverClientId =>
      _override.isEmpty ? _webClientId : _override;
}

/// [GoogleIdentity] through the `google_sign_in` plugin (Credential Manager
/// on Android, the Google SDK on iOS).
class PluginGoogleIdentity implements GoogleIdentity {
  PluginGoogleIdentity({required this._serverClientId});

  final String _serverClientId;
  final GoogleSignIn _plugin = GoogleSignIn.instance;
  Future<void>? _initialized;

  @override
  bool get isAvailable => _plugin.supportsAuthenticate();

  @override
  Future<String?> requestIdToken() async {
    try {
      await (_initialized ??= _plugin.initialize(
        serverClientId: _serverClientId,
      ));
      final account = await _plugin.authenticate();
      final token = account.authentication.idToken;
      // As on the web (auto_select off): the next sign-in asks again which
      // Google account to use. The app session does not depend on this.
      await _plugin.signOut();
      if (token == null || token.isEmpty) {
        throw const GoogleSignInFailure(misconfigured: true);
      }
      return token;
    } on GoogleSignInException catch (error) {
      return switch (error.code) {
        GoogleSignInExceptionCode.canceled => null,
        GoogleSignInExceptionCode.clientConfigurationError ||
        GoogleSignInExceptionCode.providerConfigurationError =>
          throw const GoogleSignInFailure(misconfigured: true),
        _ => throw const GoogleSignInFailure(misconfigured: false),
      };
    }
  }
}
