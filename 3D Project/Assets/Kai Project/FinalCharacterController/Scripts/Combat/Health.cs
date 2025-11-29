using UnityEngine;

public class Health : MonoBehaviour
{
    [SerializeField] int maxHP = 100;
    [SerializeField] int baseDefense = 5;
    [SerializeField] DamageCalculator calc; // optional
    [SerializeField] bool debugLogs = true;

    int currentHP;

    void Awake() { currentHP = maxHP; }

    public void TakeDamage(int incoming)
    {
        int final = calc ? calc.ComputeMitigated(incoming, baseDefense)
                         : Mathf.Max(1, incoming - baseDefense);
        currentHP = Mathf.Max(0, currentHP - final);
        if (debugLogs) Debug.Log($"{name} took {final}, HP={currentHP}/{maxHP}");
        if (currentHP == 0) Die();
    }

    void Die() { if (debugLogs) Debug.Log($"{name} died"); /* TODO: destroy */ }

    public void SetCalculator(DamageCalculator c) => calc = c;
}
