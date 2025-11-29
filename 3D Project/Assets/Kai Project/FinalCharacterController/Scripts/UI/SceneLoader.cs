using UnityEngine.SceneManagement;

public static class SceneLoader
{
    public const string MainMenu = "MainMenu";
    public const string Login    = "LoginScene";  // your current login scene name
    public const string Game     = "SampleScene3"; // your gameplay scene

    public static void LoadMainMenu() => SceneManager.LoadScene(MainMenu);
    public static void LoadLogin()    => SceneManager.LoadScene(Login);
    public static void LoadGame()     => SceneManager.LoadScene(Game);
}
