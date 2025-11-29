
using UnityEngine;

[RequireComponent(typeof(DamageCalculator))]
public class DamageCalcTester : MonoBehaviour
{
    DamageCalculator calc;                    

    [SerializeField] int baseAttack = 10;
    [SerializeField] int baseDefense = 5;
    [SerializeField] float baseCritChance = 0.1f;

    void Awake() {
        // Guaranteed to exist because of RequireComponent
        calc = GetComponent<DamageCalculator>();
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Alpha1))
        {
            bool crit;
            int dmg = calc.ComputeDamage(baseAttack, baseCritChance, out crit);
            Debug.Log($"[TEST] Damage={dmg} Crit={crit}");
        }

        if (Input.GetKeyDown(KeyCode.Alpha2))
        {
            int mitigated = calc.ComputeMitigated(20, baseDefense);
            Debug.Log($"[TEST] Mitigated={mitigated}");
        }
    }
}
