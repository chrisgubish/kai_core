using UnityEngine;

public static class CursorManager
{
    // Simple reference counting in case multiple panels open
    private static int _uiDepth = 0;

    public static void PushUI()
    {
        _uiDepth++;
        Apply();
    }

    public static void PopUI()
    {
        _uiDepth = Mathf.Max(0, _uiDepth - 1);
        Apply();
    }

    private static void Apply()
    {
        bool uiActive = _uiDepth > 0;
        Cursor.visible   = uiActive;
        Cursor.lockState = uiActive ? CursorLockMode.None : CursorLockMode.Locked;
    }

    // hard reset if needed
    public static void Reset(bool uiActive)
    {
        _uiDepth = uiActive ? 1 : 0;
        Apply();
    }
}
