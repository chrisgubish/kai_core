using UnityEngine;

public class PersistAcrossScenes : MonoBehaviour
{
    private static bool _created;

    void Awake()
    {
        if (_created) { Destroy(gameObject); return; }  // prevent duplicates
        _created = true;
        DontDestroyOnLoad(gameObject);                  // keep this object alive
    }
}
