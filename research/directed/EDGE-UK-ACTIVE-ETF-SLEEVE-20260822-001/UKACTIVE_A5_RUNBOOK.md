# UKACTIVE-A5 operating runbook

## Safety

This is a non-trading shadow process. It cannot place, preview, stage or transmit an order.

## OFFICIAL MONTH-END RUN

Run after validated month-end closing data are available, but before the next eligible XLON session closes.

## EXECUTION RUN

Run after the next eligible XLON session closes. A delayed log uses the already frozen price date and is disclosed.

## WEEKLY TELEMETRY

Run after the final valid XLON session each week. Telemetry cannot alter either model.

## NORMAL COMMAND

```powershell
.un_ukactive_a5.ps1
```

The wrapper calls AUTO mode with `--asof latest --commit-push`; the runner performs only actions allowed by the frozen calendar and state. To print without creating a signal, execution or telemetry event, use the following command. It can still append a newly available mark-to-market NAV row, as required by the operating specification:

```powershell
.un_ukactive_a5.ps1 -Mode report -NoCommitPush
```

Explicit Python examples:

```powershell
python codeun_ukactive_a5_shadow.py --mode signal --asof latest --commit-push
python codeun_ukactive_a5_shadow.py --mode execute --asof latest --commit-push
python codeun_ukactive_a5_shadow.py --mode telemetry --asof latest --commit-push
python codeun_ukactive_a5_shadow.py --mode report --asof 2026-08-21
```

If a month-end signal is first recorded after next-session close data exist, AUTO mode diagnoses it as `LATE_SIGNAL_NOT_E3` and it does not count toward 24. If SWDA / IE00B4L5Y983 remains unconfirmed in ii, A5-B booking is withheld and the open item is printed. Record any later manual core verification with its actual observation date, commit that current-only metadata before running A5, and never back-project it.

The runner refuses prospective evidence if its code, frozen config or implementation map has uncommitted changes, if the freeze tag is absent, or if the current branch is not descended from the freeze.
