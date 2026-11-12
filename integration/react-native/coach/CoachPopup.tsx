import React, { useEffect, useRef, useState } from 'react';
import { Animated, Modal, Platform, Pressable, Text, View } from 'react-native';

import { CoachPortrait } from './CoachPortrait';
import { coachFrame, typedLength } from './lines';

export type CoachPopupProps = {
  visible: boolean;
  /** one message, or several shown one after another (tap to advance) */
  messages: string | string[];
  onClose: () => void;
  /** name plate over the text */
  coachName?: string;
  /** team colors for the cap and polo, and the box accent */
  capColor?: string;
  shirtColor?: string;
  accent?: string;
  /** a pixel font from your app, if you have one; defaults to a monospace font */
  fontFamily?: string;
  /** typing speed */
  charsPerSecond?: number;
};

const NAVY = '#18143a';
const PANEL = '#30196a';
const CREAM = '#f4ebd0';
const MONO = Platform.select({ ios: 'Courier', android: 'monospace', default: 'monospace' });

/**
 * A retro dialog box that slides up over the menu: the coach on the left,
 * talking while his line types out. Tap once to finish the line, again to go
 * on (or close after the last one).
 */
export function CoachPopup({
  visible,
  messages,
  onClose,
  coachName = 'COACH',
  capColor = '#1D4FB8',
  shirtColor = '#1D4FB8',
  accent = '#f2c230',
  fontFamily = MONO,
  charsPerSecond = 38,
}: CoachPopupProps) {
  const pages = Array.isArray(messages) ? messages : [messages];
  const [page, setPage] = useState(0);
  const [t, setT] = useState(0);
  const start = useRef(0);
  const skipped = useRef(false);
  const slide = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!visible) return;
    setPage(0);
    slide.setValue(0);
    Animated.spring(slide, { toValue: 1, useNativeDriver: true, friction: 7, tension: 60 }).start();
  }, [visible, slide]);

  useEffect(() => {
    if (!visible) return;
    start.current = Date.now();
    skipped.current = false;
    setT(0);
    const id = setInterval(() => setT((Date.now() - start.current) / 1000), 33);
    return () => clearInterval(id);
  }, [visible, page]);

  const text = pages[Math.min(page, pages.length - 1)] ?? '';
  const shown = skipped.current ? text.length : typedLength(text, t, charsPerSecond);
  const done = shown >= text.length;
  const last = text[shown - 1] ?? '';
  const frame = coachFrame(t, !done, /[.,!?]/.test(last));

  const onPress = () => {
    if (!done) {
      skipped.current = true;
      setT((Date.now() - start.current) / 1000);
    } else if (page < pages.length - 1) {
      setPage(page + 1);
    } else {
      onClose();
    }
  };

  const translateY = slide.interpolate({ inputRange: [0, 1], outputRange: [260, 0] });
  return (
    <Modal transparent visible={visible} animationType="fade" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(8,6,20,0.55)' }} onPress={onPress}>
        <Animated.View
          style={{
            margin: 12,
            marginBottom: 28,
            transform: [{ translateY }],
            backgroundColor: NAVY,
            borderWidth: 4,
            borderColor: CREAM,
            padding: 4,
          }}
        >
          <View style={{ borderWidth: 2, borderColor: accent, flexDirection: 'row', padding: 10, minHeight: 132 }}>
            <View style={{ backgroundColor: PANEL, borderWidth: 3, borderColor: CREAM, marginRight: 12 }}>
              <CoachPortrait size={104} frame={frame} capColor={capColor} shirtColor={shirtColor} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={{ color: accent, fontFamily, fontWeight: 'bold', fontSize: 15, letterSpacing: 2, marginBottom: 6 }}>
                {coachName.toUpperCase()}
              </Text>
              <Text style={{ color: CREAM, fontFamily, fontSize: 15, lineHeight: 21 }}>
                {text.slice(0, shown)}
                {/* reserve the full text's height so the box doesn't grow as it types */}
                <Text style={{ color: 'transparent' }}>{text.slice(shown)}</Text>
              </Text>
              <Text style={{ color: accent, fontFamily, fontSize: 12, alignSelf: 'flex-end', marginTop: 6,
                opacity: done && Math.floor(t * 2) % 2 === 0 ? 1 : done ? 0.35 : 0 }}>
                {page < pages.length - 1 ? 'NEXT ▼' : 'CONTINUE ▼'}
              </Text>
            </View>
          </View>
        </Animated.View>
      </Pressable>
    </Modal>
  );
}
