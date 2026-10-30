# polyps/motor/

## Purpose
Choose and mount the motor that winds the string to collapse a polyp.

## Design intent (from Remy)
- Likely a simple stepper motor; not chosen. Remy wants guidance.
- Remy looked at this briefly in another repo and may hand it over later.

## Status
Not started.

## Mechanism (decided 2026-10-30)
Five finger strings end in loops at the centre. One central string hitches through all five loops and winds onto a spool on the motor. The spool must be big enough for the strings to bunch up as they wind.

The motor has to pull against the air pressure. With one central blower and a shared internal bladder the pressure stays up, so the motor must be stronger. With individual blowers the pressure can be turned down while pulling.

## Open questions (needed to size the motor)
- String pull force and travel needed to collapse one polyp against the air pressure.
- One motor per polyp, or one motor driving several.
- Spool size, and where the motor mounts relative to the skin.

## Next
- Estimate pull force and travel once the polyp shape and air pressure are known.
- Compare a few motor options (stepper vs. alternatives) in plain language.
