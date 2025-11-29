using UnityEngine;

public class MainMenuController : MonoBehaviour
{
    [SerializeField] GameObject settingsPanel; // assign in Inspector

    public void OnPlay()     => SceneLoader.LoadLogin();     // go to your login scene
    public void OnSettings() => settingsPanel.SetActive(true);
    public void OnQuit()     { Application.Quit(); }
}
