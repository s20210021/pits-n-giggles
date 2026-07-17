/**
 * Column Configuration Module for the Driver View.
 *
 * Manages which column groups are visible in the race table.
 * User preferences are persisted in localStorage.
 * Session-based overrides (e.g. fuel only in race) are transient.
 */
const t = (k) => window.__i18n.tr(k);

class ColumnConfig {
    static STORAGE_KEY = 'driver-view-column-config';
    static AUTO_PRESET_SHOWN_KEY = 'driver-view-auto-preset-shown';
    static CUSTOM_PRESET_KEY = 'driver-view-custom-preset';

    static COLUMN_GROUPS = [
        { id: 'delta',           label: t('frontend.column.label_delta') },
        { id: 'ers',             label: t('frontend.column.label_ers') },
        { id: 'warns-pens',     label: t('frontend.column.label_warns_pens') },
        { id: 'best-lap',       label: t('frontend.column.label_best_lap') },
        { id: 'last-lap',       label: t('frontend.column.label_last_lap') },
        { id: 'current-lap',    label: t('frontend.column.label_current_lap') },
        { id: 'tyre-info',      label: t('frontend.column.label_tyre_info'), children: [
            { id: 'tyre-compound',   label: t('frontend.column.label_compound_wear') },
            { id: 'tyre-age',        label: t('frontend.column.label_age_pits') },
            { id: 'tyre-pit-rejoin', label: t('frontend.column.label_pit_rejoin') },
            { id: 'tyre-temps',      label: t('frontend.column.label_temps') },
        ]},
        { id: 'wear-prediction', label: t('frontend.column.label_wear_prediction') },
        { id: 'damage',         label: t('frontend.column.label_damage') },
        { id: 'fuel',           label: t('frontend.column.label_fuel') },
    ];

    static PRESETS = [
        {
            id: 'full-race', emoji: '🏁', label: t('frontend.column.preset_full_race'),
            visible: null // all on
        },
        {
            id: 'racer', emoji: '🎮', label: t('frontend.column.preset_racer'),
            visible: ['delta', 'tyre-info', 'tyre-compound', 'tyre-age', 'last-lap', 'fuel']
        },
        {
            id: 'strategist', emoji: '📊', label: t('frontend.column.preset_strategist'),
            visible: ['delta', 'tyre-info', 'tyre-compound', 'tyre-age', 'tyre-pit-rejoin', 'tyre-temps', 'wear-prediction', 'fuel', 'best-lap']
        },
        {
            id: 'pace-hunter', emoji: '⚔️', label: t('frontend.column.preset_pace_hunter'),
            visible: ['delta', 'best-lap', 'last-lap', 'current-lap', 'ers']
        },
        {
            id: 'damage-watch', emoji: '🔧', label: t('frontend.column.preset_damage_watch'),
            visible: ['tyre-info', 'tyre-compound', 'damage', 'warns-pens']
        },
        {
            id: 'compact', emoji: '📱', label: t('frontend.column.preset_compact'),
            visible: ['tyre-info', 'tyre-compound', 'last-lap']
        },
    ];

    static getAllColumnIds() {
        const ids = [];
        ColumnConfig.COLUMN_GROUPS.forEach(g => {
            ids.push(g.id);
            if (g.children) g.children.forEach(c => ids.push(c.id));
        });
        return ids;
    }

    static findParentGroup(childId) {
        return ColumnConfig.COLUMN_GROUPS.find(g =>
            g.children?.some(c => c.id === childId)
        ) || null;
    }

    constructor() {
        this.userConfig = this._loadFromStorage();
        this.sessionOverrides = {};
        this._listeners = [];
    }

    _getDefaults() {
        const columns = {};
        ColumnConfig.COLUMN_GROUPS.forEach(g => {
            columns[g.id] = true;
            if (g.children) {
                g.children.forEach(c => { columns[c.id] = true; });
            }
        });
        return { activePreset: null, columns };
    }

    _loadFromStorage() {
        try {
            const raw = localStorage.getItem(ColumnConfig.STORAGE_KEY);
            if (raw) {
                const parsed = JSON.parse(raw);
                // Ensure all groups exist (forward-compat)
                const defaults = this._getDefaults();
                for (const key of Object.keys(defaults.columns)) {
                    if (parsed.columns[key] === undefined) {
                        parsed.columns[key] = true;
                    }
                }
                return parsed;
            }
        } catch (e) {
            console.warn('Failed to load column config from localStorage:', e);
        }
        return this._getDefaults();
    }

    _saveToStorage() {
        try {
            localStorage.setItem(ColumnConfig.STORAGE_KEY, JSON.stringify(this.userConfig));
        } catch (e) {
            console.warn('Failed to save column config to localStorage:', e);
        }
    }

    isUserEnabled(groupId) {
        return this.userConfig.columns[groupId] ?? true;
    }

    isSessionAllowed(groupId) {
        return this.sessionOverrides[groupId] ?? true;
    }

    /**
     * Returns true if a column group should actually be rendered.
     * For child groups, the parent must also be visible.
     */
    isVisible(groupId) {
        const parent = ColumnConfig.findParentGroup(groupId);
        if (parent) {
            return this.isUserEnabled(parent.id) && this.isUserEnabled(groupId) && this.isSessionAllowed(groupId);
        }
        return this.isUserEnabled(groupId) && this.isSessionAllowed(groupId);
    }

    /**
     * Set user preference for a column group.
     * Handles parent/child interactions automatically.
     */
    setUserVisible(groupId, visible) {
        this.userConfig.columns[groupId] = visible;

        // Parent toggled → set all children
        const group = ColumnConfig.COLUMN_GROUPS.find(g => g.id === groupId);
        if (group?.children) {
            group.children.forEach(c => {
                this.userConfig.columns[c.id] = visible;
            });
        }

        // Child toggled → update parent state
        const parent = ColumnConfig.findParentGroup(groupId);
        if (parent) {
            const anyChildOn = parent.children.some(c => this.userConfig.columns[c.id]);
            this.userConfig.columns[parent.id] = anyChildOn;
        }

        this.userConfig.activePreset = null;
        this._saveToStorage();
        this._notify();
    }

    /**
     * Returns the parent toggle state for UI rendering:
     * 'all' if all children on, 'none' if all off, 'indeterminate' if mixed.
     */
    getParentCheckState(parentId) {
        const group = ColumnConfig.COLUMN_GROUPS.find(g => g.id === parentId);
        if (!group?.children) return this.userConfig.columns[parentId] ? 'all' : 'none';
        const onCount = group.children.filter(c => this.userConfig.columns[c.id]).length;
        if (onCount === 0) return 'none';
        if (onCount === group.children.length) return 'all';
        return 'indeterminate';
    }

    /**
     * Apply a preset configuration.
     */
    applyPreset(presetId) {
        if (presetId === 'custom') {
            return this.applyCustomPreset();
        }
        const preset = ColumnConfig.PRESETS.find(p => p.id === presetId);
        if (!preset) return;

        const allIds = ColumnConfig.getAllColumnIds();
        if (preset.visible === null) {
            allIds.forEach(id => { this.userConfig.columns[id] = true; });
        } else {
            allIds.forEach(id => {
                this.userConfig.columns[id] = preset.visible.includes(id);
            });
        }

        this.userConfig.activePreset = presetId;
        this._saveToStorage();
        this._notify();
    }

    get activePreset() {
        return this.userConfig.activePreset;
    }

    setSessionOverride(groupId, allowed) {
        this.sessionOverrides[groupId] = allowed;
    }

    resetToDefault() {
        this.userConfig = this._getDefaults();
        this._saveToStorage();
        this._notify();
    }

    areAllUserColumnsHidden() {
        return ColumnConfig.COLUMN_GROUPS.every(g => !this.userConfig.columns[g.id]);
    }

    onChange(callback) {
        this._listeners.push(callback);
    }

    _notify() {
        this._listeners.forEach(cb => cb());
    }

    /**
     * Check if auto-preset should be applied (first visit on small screen).
     * Returns true if auto-preset was applied.
     */
    checkAutoPreset() {
        try {
            const alreadyShown = localStorage.getItem(ColumnConfig.AUTO_PRESET_SHOWN_KEY);
            const hasExistingConfig = localStorage.getItem(ColumnConfig.STORAGE_KEY);
            if (alreadyShown || hasExistingConfig) return false;

            if (window.innerWidth < 1024) {
                this.applyPreset('compact');
                localStorage.setItem(ColumnConfig.AUTO_PRESET_SHOWN_KEY, '1');
                return true;
            }
        } catch (e) {
            console.warn('Auto-preset check failed:', e);
        }
        return false;
    }

    // --- Custom Preset ---

    saveCustomPreset() {
        const visible = [];
        const allIds = ColumnConfig.getAllColumnIds();
        allIds.forEach(id => {
            if (this.userConfig.columns[id]) visible.push(id);
        });
        try {
            localStorage.setItem(ColumnConfig.CUSTOM_PRESET_KEY, JSON.stringify(visible));
        } catch (e) {
            console.warn('Failed to save custom preset:', e);
        }
        this.userConfig.activePreset = 'custom';
        this._saveToStorage();
        this._notify();
    }

    getCustomPreset() {
        try {
            const raw = localStorage.getItem(ColumnConfig.CUSTOM_PRESET_KEY);
            if (raw) return JSON.parse(raw);
        } catch (e) {
            console.warn('Failed to load custom preset:', e);
        }
        return null;
    }

    hasCustomPreset() {
        return this.getCustomPreset() !== null;
    }

    deleteCustomPreset() {
        try {
            localStorage.removeItem(ColumnConfig.CUSTOM_PRESET_KEY);
        } catch (e) {
            console.warn('Failed to delete custom preset:', e);
        }
        if (this.userConfig.activePreset === 'custom') {
            this.userConfig.activePreset = null;
            this._saveToStorage();
        }
        this._notify();
    }

    applyCustomPreset() {
        const visible = this.getCustomPreset();
        if (!visible) return;

        const allIds = ColumnConfig.getAllColumnIds();
        allIds.forEach(id => {
            this.userConfig.columns[id] = visible.includes(id);
        });
        this.userConfig.activePreset = 'custom';
        this._saveToStorage();
        this._notify();
    }
}
