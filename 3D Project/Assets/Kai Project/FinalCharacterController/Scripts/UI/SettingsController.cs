using UnityEngine;
using UnityEngine.UI;

[System.Serializable]
public class GameSettingsData
{
    public float masterVolume = 1f;
}

public class SettingsController : MonoBehaviour
{
    [SerializeField] Slider volumeSlider;

    GameSettingsData data;

    void OnEnable()
    {
        data = Load();
        volumeSlider.value = data.masterVolume;
    }

    public void OnApply()
    {
        data.masterVolume = volumeSlider.value;
        AudioListener.volume = data.masterVolume;
        Save(data);
    }

    public void OnClose() => gameObject.SetActive(false);

    // Simple JSON persistence
    const string FileName = "settings.json";
    static string Path => System.IO.Path.Combine(Application.persistentDataPath, FileName);

    static void Save(GameSettingsData d) => System.IO.File.WriteAllText(Path, JsonUtility.ToJson(d));
    static GameSettingsData Load() => System.IO.File.Exists(Path)
        ? JsonUtility.FromJson<GameSettingsData>(System.IO.File.ReadAllText(Path))
        : new GameSettingsData();
}
