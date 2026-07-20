## ADDED Requirements

### Requirement: The launcher menu icon is legible on unselected launcher rows
The app's launcher menu icon (`IMAGE_ICON`, declared with `"menuIcon": true` in `appinfo.json`) SHALL render with visible contrast against the launcher's unselected row background as well as its selected/highlighted row background, on every supported platform.

#### Scenario: Icon is visible on an unselected launcher row
- **WHEN** the app is listed in the watch launcher and its row is NOT selected
- **THEN** the icon's artwork is distinguishable from the row background (it is not drawn in the same tone as the background)

#### Scenario: Icon is visible on the selected launcher row
- **WHEN** the app's row in the launcher is selected/highlighted
- **THEN** the icon's artwork remains distinguishable from the highlighted row background

#### Scenario: Colour and black-and-white platforms are both covered
- **WHEN** the icon is rendered on a colour platform (basalt, chalk, emery, gabbro) via `timer_icon~color.png`
- **AND** on a black-and-white platform (aplite, diorite) via `timer_icon~bw.png`
- **THEN** both variants satisfy the visibility requirement above

---

### Requirement: The menu icon source artwork is not uniformly light
The menu icon source PNGs SHALL NOT consist solely of near-white opaque pixels over transparency, since the launcher draws them without recolouring and such artwork disappears against light row backgrounds.

#### Scenario: Colour variant has non-white opaque artwork
- **WHEN** `resources/images/timer_icon~color.png` is inspected
- **THEN** a substantial share of its non-transparent pixels are dark rather than near-white

#### Scenario: Regression is caught automatically
- **WHEN** the menu icon artwork is changed in a way that makes all of its opaque pixels near-white
- **THEN** an automated asset check fails and reports the icon as invisible-on-light-background
