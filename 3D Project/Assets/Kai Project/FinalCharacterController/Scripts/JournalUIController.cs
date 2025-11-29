using UnityEngine;
using TMPro;

public class JournalUIController : MonoBehaviour
{
    [Header("UI References")]
    public TMP_InputField entryInput;
    public TMP_Text charCounter;

    [Header("Character Limit")]
    public int maxCharacters = 2000;

    void Start()
    {
        UpdateCharacterCount();

        entryInput.onValueChanged.AddListener(delegate { UpdateCharacterCount(); });
    }

    void UpdateCharacterCount()
    {
        int currentLength = entryInput.text.Length;
        charCounter.text = $"{currentLength}/{maxCharacters}";
    }
}
