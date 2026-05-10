import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { useEffect, useRef, useState } from 'react';
import {
    ActivityIndicator,
    Alert,
    FlatList,
    KeyboardAvoidingView,
    Linking,
    Modal,
    Platform,
    StyleSheet,
    Switch,
    Text,
    TextInput,
    TouchableOpacity,
    View
} from 'react-native';

const API_URL = 'https://medication-app-backend.onrender.com/api';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  triage?: TriageResult | null;
}

interface TriageResult {
  level: 'EMERGENCY' | 'URGENT' | 'APPOINTMENT' | 'SELF_CARE';
  emoji: string;
  title: string;
  action: string;
  color: string;
  advice: string;
  disclaimer: string;
}

interface Medication {
  med_id: string;
  name: string;
  dosage: string;
  scheduled_times: string[];
  times_per_day: number;
  is_active: boolean;
}

interface DueMedication {
  med_id: string;
  name: string;
  dosage: string;
  time: string;
  status: 'due' | 'missed';
}

const TriageCard = ({ triage }: { triage: TriageResult }) => {
  const handleCallAmbulance = () => {
    Linking.openURL('tel:123');
  };

  return (
    <View style={[triageStyles.card, { borderLeftColor: triage.color }]}>
      <View style={[triageStyles.header, { backgroundColor: triage.color }]}>
        <Text style={triageStyles.headerEmoji}>{triage.emoji}</Text>
        <Text style={triageStyles.headerTitle}>{triage.title}</Text>
      </View>
      <View style={triageStyles.body}>
        <Text style={[triageStyles.action, { color: triage.color }]}>{triage.action}</Text>
        <Text style={triageStyles.advice}>{triage.advice}</Text>
        <Text style={triageStyles.disclaimer}>{triage.disclaimer}</Text>
        {triage.level === 'EMERGENCY' && (
          <TouchableOpacity
            style={[triageStyles.callButton, { backgroundColor: triage.color }]}
            onPress={handleCallAmbulance}
          >
            <Text style={triageStyles.callButtonText}>📞 Call 123 (Ambulance)</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
};

export default function ChatScreen() {
  const [userName, setUserName] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(true);
  const [isWaitingForBotResponse, setIsWaitingForBotResponse] = useState(false);
  const [conversationState, setConversationState] = useState('');
  const [lastIntent, setLastIntent] = useState('');
  const [medications, setMedications] = useState<Medication[]>([]);
  const [showMedicationsModal, setShowMedicationsModal] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [authScreen, setAuthScreen] = useState<'login' | 'register'>('login');
  const [showPassword, setShowPassword] = useState(false);
  const [currentScreen, setCurrentScreen] = useState<'home' | 'chat'>('home');
  const [currentDueMedication, setCurrentDueMedication] = useState<DueMedication | null>(null);
  const [previousMedications, setPreviousMedications] = useState<DueMedication[]>([]);
  const [showAboutModal, setShowAboutModal] = useState(false);

  const flatListRef = useRef<FlatList>(null);
  const notificationListener = useRef<any>();
  const responseListener = useRef<any>();

  useEffect(() => {
    loadUser();
    setupNotifications();
  }, []);

  const restoreLastMedicationNotification = async () => {
    try {
      const savedMed = await AsyncStorage.getItem('lastMedicationNotification');
      if (savedMed) {
        const med = JSON.parse(savedMed);
        setCurrentDueMedication(med);
        setCurrentScreen('home');
      }
    } catch (error) {
      console.error('Error restoring medication:', error);
    }
  };

  const saveMedicationNotification = async (med: DueMedication) => {
    try {
      await AsyncStorage.setItem('lastMedicationNotification', JSON.stringify(med));
    } catch (error) {
      console.error('Error saving medication:', error);
    }
  };

  const clearMedicationNotification = async () => {
    try {
      await AsyncStorage.removeItem('lastMedicationNotification');
    } catch (error) {
      console.error('Error clearing medication:', error);
    }
  };

  useEffect(() => {
    if (isLoggedIn && userName) {
      loadMedications(userName);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [messages]);

  const setupNotifications = async () => {
    if (Device.isDevice) {
      const { status: existingStatus } = await Notifications.getPermissionsAsync();
      let finalStatus = existingStatus;
      if (existingStatus !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
      }
      if (finalStatus !== 'granted') return;

      notificationListener.current = Notifications.addNotificationReceivedListener(async (notification) => {
        const data = notification.request.content.data;
        const medicationName = String(data.medication || '');
        const dosage = String(data.dosage || '');
        const dosageTime = String(data.dosageTime || 'Now');
        const medId = String(data.med_id || '');

        if (medicationName && medicationName !== '') {
          const savedMed = await AsyncStorage.getItem('lastMedicationNotification');
          if (savedMed) {
            const prevMed = JSON.parse(savedMed);
            if (prevMed.med_id !== medId) {
              const today = new Date().toDateString();
              const storedUser = await AsyncStorage.getItem('userName');
              if (storedUser) {
                const handledKey = `handledMeds_${storedUser}_${today}`;
                try {
                  const stored = await AsyncStorage.getItem(handledKey);
                  const handledMeds = stored ? JSON.parse(stored) : [];
                  if (!handledMeds.includes(prevMed.med_id)) {
                    handledMeds.push(prevMed.med_id);
                    await AsyncStorage.setItem(handledKey, JSON.stringify(handledMeds));
                  }
                } catch (e) {}
                try {
                  await fetch(`${API_URL}/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_name: storedUser, message: `I am skipping my dose of ${prevMed.name}` }),
                  });
                } catch (e) {}
              }
            }
          }

          const newMed: DueMedication = { med_id: medId, name: medicationName, dosage, time: dosageTime, status: 'due' };
          setCurrentDueMedication(newMed);
          await saveMedicationNotification(newMed);
          setCurrentScreen('home');
        }
      });

      responseListener.current = Notifications.addNotificationResponseReceivedListener(async (response) => {
        const data = response.notification.request.content.data;
        const medicationName = String(data.medication || '');
        const dosage = String(data.dosage || '');
        const dosageTime = String(data.dosageTime || 'Now');
        const medId = String(data.med_id || '');

        if (medicationName && medicationName !== '') {
          const newMed: DueMedication = { med_id: medId, name: medicationName, dosage, time: dosageTime, status: 'due' };
          await AsyncStorage.setItem('lastMedicationNotification', JSON.stringify(newMed));
          setCurrentDueMedication(newMed);
          setCurrentScreen('home');
          const storedUser = await AsyncStorage.getItem('userName');
          if (storedUser && !isLoggedIn) {
            setUserName(storedUser);
            setIsLoggedIn(true);
            initializeChat(storedUser);
            loadMedications(storedUser);
          }
        }
      });
    }

    return () => {
      if (notificationListener.current) Notifications.removeNotificationSubscription(notificationListener.current);
      if (responseListener.current) Notifications.removeNotificationSubscription(responseListener.current);
    };
  };

  const scheduleNotificationsForMedications = async (meds: Medication[]) => {
    try {
      await Notifications.cancelAllScheduledNotificationsAsync();
      for (const med of meds) {
        if (!med.is_active) continue;
        for (const timeStr of med.scheduled_times) {
          try {
            const [hours, minutes] = timeStr.split(':').map(Number);
            if (isNaN(hours) || isNaN(minutes)) continue;
            const ampm = hours >= 12 ? 'pm' : 'am';
            const displayHour = hours % 12 || 12;
            await Notifications.scheduleNotificationAsync({
              content: {
                title: '💊 Medication Reminder',
                body: `Time to take ${med.name} (${med.dosage})`,
                sound: 'default',
                badge: 1,
                data: { medication: med.name, dosage: med.dosage, dosageTime: `${displayHour}${ampm}`, med_id: med.med_id },
              },
              trigger: { type: Notifications.SchedulableTriggerInputTypes.DAILY, hour: hours, minute: minutes },
            });
          } catch (error) {
            console.error(`Failed to schedule notification for ${med.name}:`, error);
          }
        }
      }
    } catch (error) {
      console.error('Error scheduling notifications:', error);
    }
  };

  const handleQuickAction = async (action: 'taken' | 'later' | 'skip') => {
    if (!currentDueMedication) { Alert.alert('Error', 'No medication to record'); return; }
    if (!isLoggedIn) { Alert.alert('Error', 'Please login first'); return; }

    try {
      let success = false;

      if (action === 'taken') {
        const response = await fetch(`${API_URL}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_name: userName, message: `I took ${currentDueMedication.name}` }),
        });
        const data = await response.json();
        success = data.success;

      } else if (action === 'later') {
        try {
          await Notifications.scheduleNotificationAsync({
            content: {
              title: '💊 Medication Reminder',
              body: `Don't forget to take ${currentDueMedication.name} (${currentDueMedication.dosage})`,
              sound: 'default',
              data: { medication: currentDueMedication.name, dosage: currentDueMedication.dosage, dosageTime: currentDueMedication.time, med_id: currentDueMedication.med_id },
            },
            trigger: { type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL, seconds: 1200, repeats: false },
          });
        } catch (e) { console.error('Later notification error:', e); }
        Alert.alert('Success', `${currentDueMedication.name} - ⏰ Will remind you in 20 minutes`);
        setCurrentDueMedication(null);
        await clearMedicationNotification();
        return;

      } else if (action === 'skip') {
        const response = await fetch(`${API_URL}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_name: userName, message: `I am skipping my dose of ${currentDueMedication.name}` }),
        });
        const data = await response.json();
        success = data.success;
      }

      if (success) {
        const actionLabel = action === 'taken' ? '✅ Recorded as taken' : '⚠️ Recorded as skipped';
        Alert.alert('Success', `${currentDueMedication.name} - ${actionLabel}`);
        const today = new Date().toDateString();
        const handledKey = `handledMeds_${userName}_${today}`;
        try {
          const stored = await AsyncStorage.getItem(handledKey);
          const handledMeds = stored ? JSON.parse(stored) : [];
          handledMeds.push(currentDueMedication.med_id);
          await AsyncStorage.setItem(handledKey, JSON.stringify(handledMeds));
        } catch (e) {}
        setCurrentDueMedication(null);
        await clearMedicationNotification();
        setPreviousMedications(prev => [...prev, { ...currentDueMedication, status: action === 'taken' ? 'due' : 'missed' }]);
      } else {
        Alert.alert('Error', 'Could not process action');
      }
    } catch (error) {
      Alert.alert('Error', 'Connection error. Please try again.');
    }
  };

  const deleteMedication = async (medId: string, medName: string) => {
    Alert.alert('Delete Medication', `Are you sure you want to delete ${medName}?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive',
        onPress: async () => {
          try {
            const response = await fetch(`${API_URL}/medication/delete`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ user_name: userName, med_id: medId }),
            });
            const data = await response.json();
            if (data.success) { loadMedications(userName); }
            else { Alert.alert('Error', 'Could not delete medication'); }
          } catch (error) { Alert.alert('Error', 'Could not delete medication'); }
        },
      },
    ]);
  };

  const toggleMedication = async (medId: string, currentStatus: boolean) => {
    try {
      const response = await fetch(`${API_URL}/medication/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_name: userName, med_id: medId, is_active: !currentStatus }),
      });
      const data = await response.json();
      if (data.success) {
        const updatedMeds = medications.map(med => med.med_id === medId ? { ...med, is_active: !currentStatus } : med);
        setMedications(updatedMeds);
        await scheduleNotificationsForMedications(updatedMeds);
      } else { Alert.alert('Error', 'Failed to toggle medication'); }
    } catch (error) { Alert.alert('Error', 'Could not toggle medication'); }
  };

  const checkForDueMedications = async (user: string) => {
    try {
      const today = new Date().toDateString();
      const handledKey = `handledMeds_${user}_${today}`;
      let handledMeds: string[] = [];
      try {
        const stored = await AsyncStorage.getItem(handledKey);
        if (stored) handledMeds = JSON.parse(stored);
      } catch (e) {}

      const response = await fetch(`${API_URL}/medications?user_name=${user}`);
      const data = await response.json();
      if (data.success && data.medications) {
        const now = new Date();
        const currentMinutes = now.getHours() * 60 + now.getMinutes();
        let closestMed: DueMedication | null = null;
        let closestDiff = Infinity;

        for (const med of data.medications) {
          if (!med.is_active) continue;
          for (const timeStr of med.scheduled_times) {
            const [hours, minutes] = timeStr.split(':').map(Number);
            const scheduledMinutes = hours * 60 + minutes;
            const diffMinutes = currentMinutes - scheduledMinutes;
            const handledId = `${med.med_id}_${hours}:${String(minutes).padStart(2, '0')}`;
            if (handledMeds.includes(handledId)) continue;
            if (diffMinutes >= 0 && diffMinutes <= 180) {
              if (diffMinutes < closestDiff) {
                closestDiff = diffMinutes;
                const ampm = hours >= 12 ? 'pm' : 'am';
                const displayHour = hours % 12 || 12;
                closestMed = {
                  med_id: `${med.med_id}_${hours}:${String(minutes).padStart(2, '0')}`,
                  name: med.name, dosage: med.dosage,
                  time: `${displayHour}${ampm}`, status: 'due',
                };
              }
            }
          }
        }
        if (closestMed) { setCurrentDueMedication(closestMed); await saveMedicationNotification(closestMed); }
      }
    } catch (error) { console.error('Error checking due medications:', error); }
  };

  const loadUser = async () => {
    try {
      setLoading(false);
      await restoreLastMedicationNotification();
    } catch (error) { setLoading(false); }
  };

  const loadMedications = async (user: string) => {
    try {
      const response = await fetch(`${API_URL}/medications?user_name=${user}`);
      const data = await response.json();
      if (data.success && data.medications) {
        setMedications(data.medications);
        await scheduleNotificationsForMedications(data.medications);
        if (currentDueMedication) {
          const medIdBase = currentDueMedication.med_id.split('_')[0];
          const stillExists = data.medications.some((m: any) => m.med_id === medIdBase);
          if (!stillExists) { setCurrentDueMedication(null); await clearMedicationNotification(); }
        }
      }
    } catch (error) { console.error('Error loading medications:', error); }
  };

  const handleLogin = async () => {
    if (!userName.trim()) { Alert.alert('Error', 'Please enter your username'); return; }
    if (!password.trim()) { Alert.alert('Error', 'Please enter your password'); return; }
    try {
      const response = await fetch(`${API_URL}/user/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_name: userName.trim(), password }),
      });
      const data = await response.json();
      if (data.success) {
        await AsyncStorage.setItem('userName', userName.trim());
        setMedications([]); setMessages([]);
        setIsLoggedIn(true);
        initializeChat(userName.trim());
        loadMedications(userName.trim());
        setTimeout(async () => {
          await restoreLastMedicationNotification();
          checkForDueMedications(userName.trim());
        }, 800);
      } else { Alert.alert('Login Failed', data.error || 'Invalid username or password'); }
    } catch (error) { Alert.alert('Error', 'Could not connect to server.'); }
  };

  const handleRegister = async () => {
    if (!userName.trim()) { Alert.alert('Error', 'Please enter a username'); return; }
    if (userName.trim().length < 3) { Alert.alert('Error', 'Username must be at least 3 characters'); return; }
    if (!/^[a-zA-Z0-9_]+$/.test(userName.trim())) { Alert.alert('Error', 'Username can only contain letters, numbers, and underscores'); return; }
    if (!password.trim()) { Alert.alert('Error', 'Please enter a password'); return; }
    if (password.trim().length < 6) { Alert.alert('Error', 'Password must be at least 6 characters'); return; }
    if (password !== confirmPassword) { Alert.alert('Error', 'Passwords do not match'); return; }
    try {
      const response = await fetch(`${API_URL}/user/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: userName.trim(), password }),
      });
      const data = await response.json();
      if (data.success) {
        await AsyncStorage.setItem('userName', userName.trim());
        setMedications([]); setMessages([]);
        setIsLoggedIn(true);
        initializeChat(userName.trim());
        loadMedications(userName.trim());
      } else { Alert.alert('Registration Failed', data.error || 'Could not create account'); }
    } catch (error) { Alert.alert('Error', 'Could not connect to server.'); }
  };

  const initializeChat = (user: string) => {
    setMessages([{ id: Date.now().toString(), text: `Welcome! I'm here to help you manage your medications.\n\nYou can now chat with me naturally!`, sender: 'bot', timestamp: new Date() }]);
    setConversationState(''); setLastIntent('');
  };

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;
    const userMessage: Message = { id: Date.now().toString(), text: inputText, sender: 'user', timestamp: new Date() };
    setMessages((prev) => [...prev, userMessage]);
    setInputText('');
    setIsWaitingForBotResponse(true);
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_name: userName, message: inputText, conversation_state: conversationState, last_intent: lastIntent }),
      });
      const data = await response.json();
      if (data.success) {
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), text: data.message, sender: 'bot', timestamp: new Date(), triage: data.triage || null }]);
        if (data.in_conversation) { setConversationState(data.conversation_state || ''); setLastIntent(data.last_intent || lastIntent); }
        else { setConversationState(''); setLastIntent(''); }
        setTimeout(() => { loadMedications(userName); }, 500);
      } else {
        setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), text: 'Sorry, I could not understand that.', sender: 'bot', timestamp: new Date() }]);
      }
    } catch (error) {
      setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), text: '⚠️ Connection error.', sender: 'bot', timestamp: new Date() }]);
    } finally { setIsWaitingForBotResponse(false); }
  };

  const HomeScreen = () => (
    <>
      <View style={styles.homeContainer}>
        <View style={styles.homeHeader}>
          <View style={styles.homeHeaderContent}>
            <View>
              <Text style={styles.homeTitle}>💊 Medication Reminder</Text>
              <Text style={styles.homeSubtitle}>Quick Actions</Text>
            </View>
            <TouchableOpacity style={styles.infoButton} onPress={() => setShowAboutModal(true)}>
              <Text style={styles.infoButtonText}>ℹ️</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.homeContent}>
          <View style={styles.nameSelectionCard}>
            <View style={styles.userAvatarRow}>
              <View style={styles.avatarCircle}>
                <View style={styles.avatarHead} />
                <View style={styles.avatarBody} />
              </View>
              <View style={styles.userInfo}>
                <Text style={styles.nameSelectionLabel}>Current User</Text>
                <Text style={styles.nameSelectionText}>{userName}</Text>
              </View>
              <TouchableOpacity
                style={styles.changeUserButton}
                onPress={async () => {
                  await AsyncStorage.removeItem('userName');
                  setIsLoggedIn(false); setUserName(''); setPassword(''); setConfirmPassword(''); setAuthScreen('login');
                }}
              >
                <Text style={styles.switchIcon}>↻👤</Text>
                <Text style={styles.changeUserButtonText}>Switch</Text>
              </TouchableOpacity>
            </View>
          </View>

          {currentDueMedication && (
            <View style={styles.dueMedicationCard}>
              <Text style={styles.dueMedicationLabel}>Current Medication Due</Text>
              <Text style={styles.dueMedicationName}>{currentDueMedication.name}</Text>
              <Text style={styles.dueMedicationDetails}>{currentDueMedication.dosage} • {currentDueMedication.time}</Text>
              <View style={styles.quickActionsContainer}>
                <TouchableOpacity style={[styles.quickActionButton, styles.takenButton]} onPress={() => handleQuickAction('taken')}>
                  <Text style={styles.quickActionButtonText}>✓ Taken</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.quickActionButton, styles.laterButton]} onPress={() => handleQuickAction('later')}>
                  <Text style={styles.quickActionButtonText}>⏰ Later</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.quickActionButton, styles.skipButton]} onPress={() => handleQuickAction('skip')}>
                  <Text style={styles.quickActionButtonText}>✕ Skip</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}

          {previousMedications.length > 0 && (
            <View style={styles.previousMedsSection}>
              <Text style={styles.previousMedsTitle}>Recent Actions</Text>
              {previousMedications.slice(-3).map((med, index) => (
                <View key={index} style={styles.previousMedItem}>
                  <View>
                    <Text style={styles.previousMedName}>{med.name}</Text>
                    <Text style={styles.previousMedStatus}>{med.status === 'missed' ? '⚠️ Missed' : '✅ Taken'}</Text>
                  </View>
                </View>
              ))}
            </View>
          )}

          <View style={styles.homeButtonsContainer}>
            <TouchableOpacity style={[styles.homeButton, styles.chatButton]} onPress={() => setCurrentScreen('chat')}>
              <Text style={styles.homeButtonText}>💬 Open Chat</Text>
              <Text style={styles.homeButtonSubtext}>Ask DoseMate anything</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.homeButton, styles.medsManageButton]} onPress={() => setShowMedicationsModal(true)}>
              <Text style={styles.homeButtonText}>💊 Manage Medications ({medications.length})</Text>
              <Text style={styles.homeButtonSubtext}>View and edit your medications</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>

      <Modal visible={showMedicationsModal} transparent={true} animationType="slide" onRequestClose={() => setShowMedicationsModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Your Medications</Text>
              <TouchableOpacity onPress={() => setShowMedicationsModal(false)}>
                <Text style={styles.modalCloseButton}>✕</Text>
              </TouchableOpacity>
            </View>
            {medications.length === 0 ? (
              <Text style={styles.noMedicationsText}>No medications yet. Add one to get started!</Text>
            ) : (
              <FlatList
                data={medications}
                keyExtractor={(item) => item.med_id}
                renderItem={({ item }) => (
                  <View style={styles.medicationItem}>
                    <View style={styles.medicationInfo}>
                      <Text style={styles.medicationName}>{item.name}</Text>
                      <Text style={styles.medicationDetails}>{item.dosage} • {item.times_per_day}x daily</Text>
                      <Text style={styles.medicationTimes}>{item.scheduled_times.join(', ')}</Text>
                    </View>
                    <View style={styles.medItemActions}>
                      <Switch
                        value={item.is_active}
                        onValueChange={() => toggleMedication(item.med_id, item.is_active)}
                        trackColor={{ false: '#767577', true: '#81C784' }}
                        thumbColor={item.is_active ? '#007AFF' : '#f4f3f4'}
                      />
                      <TouchableOpacity style={styles.deleteButton} onPress={() => deleteMedication(item.med_id, item.name)}>
                        <Text style={styles.deleteButtonText}>🗑️</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                )}
              />
            )}
          </View>
        </View>
      </Modal>

      <Modal visible={showAboutModal} transparent={true} animationType="slide" onRequestClose={() => setShowAboutModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { maxHeight: '90%' }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>About DoseMate</Text>
              <TouchableOpacity onPress={() => setShowAboutModal(false)}>
                <Text style={styles.modalCloseButton}>✕</Text>
              </TouchableOpacity>
            </View>
            <FlatList
              data={[
                { key: 'intro', title: '💊 What is DoseMate?', content: 'DoseMate is an AI-powered medication reminder assistant that helps you manage your medications, track doses, and get instant health guidance through a natural chat interface.' },
                { key: 'chat', title: '💬 Chat Assistant', content: 'Talk to DoseMate naturally:\n• "Remind me to take Panadol at 8am"\n• "I took my medication"\n• "Delete Panadol"\n• "What is my schedule today?"' },
                { key: 'triage', title: '🚨 Symptom Triage', content: 'Describe your symptoms and DoseMate will assess urgency:\n• 🔴 EMERGENCY — Call ambulance immediately\n• 🟠 URGENT — Visit ER soon\n• 🟡 APPOINTMENT — See a doctor\n• 🟢 SELF_CARE — Rest and home remedies' },
                { key: 'treatment', title: '💡 Treatment Information', content: 'Ask about your medications:\n• "What are the side effects of Panadol?"\n• "How do I take Ibuprofen?"\n• "What foods should I avoid with Aspirin?"\n• "What if I miss a dose of Metformin?"' },
                { key: 'actions', title: '⚡ Quick Actions', content: 'When a medication is due, you can:\n• ✅ Taken — Record dose as taken\n• ⏰ Later — Snooze reminder 20 minutes\n• ✕ Skip — Record dose as skipped' },
                { key: 'manage', title: '⚙️ Manage Medications', content: 'From the home screen:\n• Toggle medications on/off\n• Delete medications with the 🗑️ button\n• View scheduled times and dosage' },
                { key: 'dev', title: '👨‍💻 Developer', content: 'Developed by Omar Khaled\nSupervised by Dr. Mahmoud El-ghorab\nFinal Year Project — 2026' },
              ]}
              keyExtractor={(item) => item.key}
              renderItem={({ item }) => (
                <View style={styles.aboutSection}>
                  <Text style={styles.aboutSectionTitle}>{item.title}</Text>
                  <Text style={styles.aboutSectionContent}>{item.content}</Text>
                </View>
              )}
            />
          </View>
        </View>
      </Modal>
    </>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  if (!isLoggedIn) {
    if (authScreen === 'register') {
      return (
        <View style={styles.loginContainer}>
          <Text style={styles.loginTitle}>💊 DoseMate</Text>
          <Text style={styles.loginSubtitle}>Create Account</Text>
          <TextInput style={styles.loginInput} placeholder="Username (min 3 characters)" value={userName} onChangeText={setUserName} autoCapitalize="none" placeholderTextColor="#999" />
          <TextInput style={styles.loginInput} placeholder="Password (min 6 characters)" value={password} onChangeText={setPassword} secureTextEntry={!showPassword} autoCapitalize="none" placeholderTextColor="#999" />
          <TextInput style={styles.loginInput} placeholder="Confirm Password" value={confirmPassword} onChangeText={setConfirmPassword} secureTextEntry={!showPassword} autoCapitalize="none" placeholderTextColor="#999" />
          <TouchableOpacity onPress={() => setShowPassword(!showPassword)} style={styles.showPasswordButton}>
            <Text style={styles.showPasswordText}>{showPassword ? '🙈 Hide Password' : '👁 Show Password'}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.loginButton} onPress={handleRegister}>
            <Text style={styles.loginButtonText}>Create Account</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => { setAuthScreen('login'); setPassword(''); setConfirmPassword(''); }}>
            <Text style={styles.switchAuthText}>Already have an account? Login</Text>
          </TouchableOpacity>
        </View>
      );
    }

    return (
      <View style={styles.loginContainer}>
        <Text style={styles.loginTitle}>💊 DoseMate</Text>
        <Text style={styles.loginSubtitle}>Medication Reminder Assistant</Text>
        <TextInput style={styles.loginInput} placeholder="Username" value={userName} onChangeText={setUserName} autoCapitalize="none" placeholderTextColor="#999" />
        <TextInput style={styles.loginInput} placeholder="Password" value={password} onChangeText={setPassword} secureTextEntry={!showPassword} autoCapitalize="none" placeholderTextColor="#999" />
        <TouchableOpacity onPress={() => setShowPassword(!showPassword)} style={styles.showPasswordButton}>
          <Text style={styles.showPasswordText}>{showPassword ? '🙈 Hide Password' : '👁 Show Password'}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.loginButton} onPress={handleLogin}>
          <Text style={styles.loginButtonText}>Login</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => { setAuthScreen('register'); setPassword(''); setConfirmPassword(''); }}>
          <Text style={styles.switchAuthText}>Don't have an account? Create one</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (currentScreen === 'home') return <HomeScreen />;

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.container} keyboardVerticalOffset={0}>
      <View style={styles.header}>
        <View style={styles.headerContent}>
          <View>
            <Text style={styles.headerTitle}>MEDICATION REMINDER CHATBOT</Text>
            <Text style={styles.headerSubtitle}>Hello, {userName}! 👋</Text>
          </View>
          <View style={styles.headerButtons}>
            <TouchableOpacity style={styles.homeIconButton} onPress={() => { setCurrentScreen('home'); if (userName) loadMedications(userName); }}>
              <Text style={styles.homeIconText}>🏠</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>

      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={[styles.messageContainer, item.sender === 'user' ? styles.userMessageContainer : styles.botMessageContainer]}>
            {item.sender === 'bot' && item.triage ? (
              <TriageCard triage={item.triage} />
            ) : (
              <View style={[styles.messageBubble, item.sender === 'user' ? styles.userBubble : styles.botBubble]}>
                <Text style={[styles.messageText, item.sender === 'user' ? styles.userMessageText : styles.botMessageText]}>{item.text}</Text>
              </View>
            )}
            {item.sender === 'bot' && !item.triage && <Text style={styles.botLabel}>Bot</Text>}
          </View>
        )}
        inverted={false}
        contentContainerStyle={styles.messagesContent}
        scrollEnabled={true}
      />

      {isWaitingForBotResponse && (
        <View style={styles.messageContainer}>
          <View style={[styles.messageBubble, styles.botBubble]}>
            <Text style={styles.botMessageText}>...</Text>
          </View>
        </View>
      )}

      <View style={styles.inputContainer}>
        <TextInput style={styles.input} placeholder="You: " placeholderTextColor="#999" value={inputText} onChangeText={setInputText} editable={!isWaitingForBotResponse} multiline maxLength={500} />
        <TouchableOpacity style={[styles.sendButton, (!inputText.trim() || isWaitingForBotResponse) && styles.sendButtonDisabled]} onPress={handleSendMessage} disabled={!inputText.trim() || isWaitingForBotResponse}>
          <Text style={styles.sendButtonText}>Send</Text>
        </TouchableOpacity>
      </View>

      <Modal visible={showMedicationsModal} transparent={true} animationType="slide" onRequestClose={() => setShowMedicationsModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Your Medications</Text>
              <TouchableOpacity onPress={() => setShowMedicationsModal(false)}>
                <Text style={styles.modalCloseButton}>✕</Text>
              </TouchableOpacity>
            </View>
            {medications.length === 0 ? (
              <Text style={styles.noMedicationsText}>No medications yet. Add one to get started!</Text>
            ) : (
              <FlatList
                data={medications}
                keyExtractor={(item) => item.med_id}
                renderItem={({ item }) => (
                  <View style={styles.medicationItem}>
                    <View style={styles.medicationInfo}>
                      <Text style={styles.medicationName}>{item.name}</Text>
                      <Text style={styles.medicationDetails}>{item.dosage} • {item.times_per_day}x daily</Text>
                      <Text style={styles.medicationTimes}>{item.scheduled_times.join(', ')}</Text>
                    </View>
                    <Switch value={item.is_active} onValueChange={() => toggleMedication(item.med_id, item.is_active)} trackColor={{ false: '#767577', true: '#81C784' }} thumbColor={item.is_active ? '#007AFF' : '#f4f3f4'} />
                  </View>
                )}
              />
            )}
          </View>
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const triageStyles = StyleSheet.create({
  card: { borderRadius: 12, overflow: 'hidden', borderLeftWidth: 5, marginVertical: 5, backgroundColor: 'white', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.15, shadowRadius: 4, elevation: 4, maxWidth: '90%' },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 15, paddingVertical: 12, gap: 8 },
  headerEmoji: { fontSize: 20 },
  headerTitle: { color: 'white', fontWeight: 'bold', fontSize: 15, flex: 1 },
  body: { padding: 15, gap: 8 },
  action: { fontWeight: 'bold', fontSize: 14 },
  advice: { fontSize: 13, color: '#444', lineHeight: 20 },
  disclaimer: { fontSize: 11, color: '#888', fontStyle: 'italic', marginTop: 4 },
  callButton: { marginTop: 10, paddingVertical: 12, borderRadius: 8, alignItems: 'center' },
  callButtonText: { color: 'white', fontWeight: 'bold', fontSize: 15 },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFFFFF' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 10, fontSize: 16, color: '#666' },
  loginContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20, backgroundColor: '#007AFF' },
  loginTitle: { fontSize: 32, fontWeight: 'bold', color: 'white', marginBottom: 10, textAlign: 'center' },
  loginSubtitle: { fontSize: 16, color: 'white', marginBottom: 40, opacity: 0.9 },
  loginInput: { width: '100%', backgroundColor: 'white', padding: 15, borderRadius: 10, fontSize: 16, marginBottom: 20, color: '#000' },
  loginButton: { width: '100%', backgroundColor: 'white', padding: 15, borderRadius: 10, alignItems: 'center', marginBottom: 15 },
  loginButtonText: { color: '#007AFF', fontSize: 18, fontWeight: 'bold' },
  showPasswordButton: { alignSelf: 'flex-start', marginBottom: 15 },
  showPasswordText: { color: 'rgba(255,255,255,0.8)', fontSize: 14 },
  switchAuthText: { color: 'white', fontSize: 14, textDecorationLine: 'underline', marginTop: 10 },
  onboardingContainer: { flex: 1, backgroundColor: '#F9F9F9' },
  onboardingContent: { padding: 20, paddingTop: 50 },
  onboardingTitle: { fontSize: 28, fontWeight: 'bold', color: '#007AFF', marginBottom: 10, textAlign: 'center' },
  onboardingSubtitle: { fontSize: 16, color: '#666', marginBottom: 30, textAlign: 'center' },
  fieldContainer: { marginBottom: 25 },
  fieldLabel: { fontSize: 16, fontWeight: 'bold', color: '#333', marginBottom: 10 },
  fieldHint: { fontSize: 12, color: '#999', marginBottom: 8 },
  buttonGroup: { flexDirection: 'row', gap: 10, justifyContent: 'space-between' },
  groupButton: { flex: 1, paddingVertical: 12, paddingHorizontal: 15, borderRadius: 8, backgroundColor: '#F0F0F0', borderWidth: 2, borderColor: '#E0E0E0', alignItems: 'center' },
  groupButtonActive: { backgroundColor: '#007AFF', borderColor: '#007AFF' },
  groupButtonText: { fontSize: 14, fontWeight: '600', color: '#666' },
  groupButtonTextActive: { color: 'white' },
  allergiesInput: { backgroundColor: 'white', borderWidth: 1, borderColor: '#E0E0E0', borderRadius: 10, padding: 12, fontSize: 14, color: '#333', minHeight: 80 },
  onboardingSaveButton: { backgroundColor: '#007AFF', paddingVertical: 15, borderRadius: 10, alignItems: 'center', marginBottom: 10 },
  onboardingSaveButtonText: { color: 'white', fontWeight: 'bold', fontSize: 16 },
  onboardingSkipButton: { paddingVertical: 12, alignItems: 'center', marginBottom: 30 },
  onboardingSkipButtonText: { color: '#007AFF', fontWeight: '600', fontSize: 14 },
  homeContainer: { flex: 1, backgroundColor: '#D6E8FF' },
  homeHeader: { backgroundColor: '#007AFF', padding: 20, paddingTop: 50, paddingBottom: 30 },
  homeHeaderContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  infoButton: { backgroundColor: 'rgba(255,255,255,0.2)', width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  infoButtonText: { fontSize: 18 },
  aboutSection: { paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  aboutSectionTitle: { fontSize: 15, fontWeight: 'bold', color: '#007AFF', marginBottom: 6 },
  aboutSectionContent: { fontSize: 13, color: '#444', lineHeight: 20 },
  homeTitle: { fontSize: 24, fontWeight: 'bold', color: 'white' },
  homeSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.8)', marginTop: 5 },
  homeContent: { flex: 1, padding: 20 },
  nameSelectionCard: { backgroundColor: 'white', borderRadius: 12, padding: 20, marginBottom: 20, borderLeftWidth: 5, borderLeftColor: '#007AFF', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  userAvatarRow: { flexDirection: 'row', alignItems: 'center' },
  avatarCircle: { width: 55, height: 55, borderRadius: 28, backgroundColor: '#007AFF', alignItems: 'center', justifyContent: 'flex-end', overflow: 'hidden', marginRight: 15 },
  avatarHead: { width: 22, height: 22, borderRadius: 11, backgroundColor: 'rgba(255,255,255,0.85)', position: 'absolute', top: 10 },
  avatarBody: { width: 38, height: 28, borderRadius: 19, backgroundColor: 'rgba(255,255,255,0.85)', marginBottom: -5 },
  userInfo: { flex: 1 },
  nameSelectionLabel: { fontSize: 12, color: '#999', fontWeight: '600', marginBottom: 5 },
  nameSelectionText: { fontSize: 20, fontWeight: 'bold', color: '#007AFF' },
  changeUserButton: { backgroundColor: '#007AFF', paddingVertical: 8, paddingHorizontal: 12, borderRadius: 20, alignItems: 'center', flexDirection: 'row', gap: 4 },
  changeUserButtonText: { color: 'white', fontWeight: '600', fontSize: 13 },
  switchIcon: { fontSize: 13 },
  dueMedicationCard: { backgroundColor: 'white', borderRadius: 12, padding: 20, marginBottom: 20, borderLeftWidth: 5, borderLeftColor: '#007AFF', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  dueMedicationLabel: { fontSize: 12, color: '#999', fontWeight: '600', marginBottom: 5 },
  dueMedicationName: { fontSize: 22, fontWeight: 'bold', color: '#007AFF', marginBottom: 5 },
  dueMedicationDetails: { fontSize: 14, color: '#666', marginBottom: 20 },
  quickActionsContainer: { flexDirection: 'row', gap: 10, justifyContent: 'space-between' },
  quickActionButton: { flex: 1, paddingVertical: 12, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  quickActionButtonText: { color: 'white', fontWeight: 'bold', fontSize: 13 },
  takenButton: { backgroundColor: '#4CAF50' },
  laterButton: { backgroundColor: '#FF9800' },
  skipButton: { backgroundColor: '#F44336' },
  previousMedsSection: { marginBottom: 20 },
  previousMedsTitle: { fontSize: 14, fontWeight: 'bold', color: '#666', marginBottom: 10 },
  previousMedItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F0F0F0' },
  previousMedName: { fontSize: 14, fontWeight: '600', color: '#333' },
  previousMedStatus: { fontSize: 12, color: '#999', marginTop: 4 },
  homeButtonsContainer: { flexDirection: 'column', gap: 10, marginTop: 'auto' },
  homeButton: { paddingVertical: 10, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  chatButton: { backgroundColor: '#007AFF' },
  medsManageButton: { backgroundColor: '#17A2B8' },
  homeButtonText: { color: 'white', fontWeight: 'bold', fontSize: 16 },
  homeButtonSubtext: { color: 'rgba(255,255,255,0.8)', fontSize: 14, marginTop: 3 },
  header: { backgroundColor: '#007AFF', padding: 20, paddingTop: 50, paddingBottom: 20 },
  headerContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle: { fontSize: 18, fontWeight: 'bold', color: 'white' },
  headerSubtitle: { fontSize: 14, color: 'rgba(255,255,255,0.8)', marginTop: 8 },
  headerButtons: { flexDirection: 'row', gap: 10, alignItems: 'center' },
  homeIconButton: { backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8 },
  homeIconText: { fontSize: 18 },
  medsButton: { backgroundColor: 'rgba(255,255,255,0.3)', paddingHorizontal: 15, paddingVertical: 8, borderRadius: 20 },
  medsButtonText: { color: 'white', fontWeight: 'bold', fontSize: 16 },
  messagesContent: { paddingHorizontal: 10, paddingVertical: 10 },
  messageContainer: { marginVertical: 5, marginHorizontal: 10 },
  userMessageContainer: { alignItems: 'flex-end' },
  botMessageContainer: { alignItems: 'flex-start' },
  messageBubble: { maxWidth: '85%', paddingHorizontal: 15, paddingVertical: 12, borderRadius: 8 },
  userBubble: { backgroundColor: '#E8E8E8' },
  botBubble: { backgroundColor: '#F5F5F5', borderLeftWidth: 2, borderLeftColor: '#007AFF' },
  messageText: { fontSize: 15, lineHeight: 20 },
  userMessageText: { color: '#000' },
  botMessageText: { color: '#000' },
  botLabel: { fontSize: 12, color: '#007AFF', marginTop: 4, marginHorizontal: 10, fontWeight: '600' },
  inputContainer: { flexDirection: 'row', paddingHorizontal: 10, paddingVertical: 12, backgroundColor: '#F2F2F7', borderTopWidth: 1, borderTopColor: '#E5E5EA', gap: 10, paddingBottom: Platform.OS === 'ios' ? 20 : 12 },
  input: { flex: 1, backgroundColor: 'white', borderRadius: 6, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15, maxHeight: 100, color: '#000', borderWidth: 1, borderColor: '#E0E0E0' },
  sendButton: { paddingHorizontal: 20, paddingVertical: 10, backgroundColor: '#007AFF', borderRadius: 6, justifyContent: 'center' },
  sendButtonDisabled: { backgroundColor: '#CCCCCC' },
  sendButtonText: { color: 'white', fontWeight: '600', fontSize: 14 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: 'white', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: '80%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15 },
  modalTitle: { fontSize: 20, fontWeight: 'bold', color: '#007AFF' },
  modalCloseButton: { fontSize: 28, color: '#999', fontWeight: 'bold' },
  medicationItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 15, borderBottomWidth: 1, borderBottomColor: '#E5E5EA' },
  medicationInfo: { flex: 1, marginRight: 10 },
  medicationName: { fontSize: 16, fontWeight: '600', color: '#000' },
  medicationDetails: { fontSize: 14, color: '#666', marginTop: 4 },
  medicationTimes: { fontSize: 12, color: '#999', marginTop: 2 },
  medItemActions: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  deleteButton: { padding: 6 },
  deleteButtonText: { fontSize: 20 },
  swipeableRow: { backgroundColor: 'white' },
  noMedicationsText: { fontSize: 14, color: '#999', textAlign: 'center', marginTop: 20 },
  pickerContainer: { backgroundColor: 'white', borderRadius: 10, borderWidth: 1, borderColor: '#E0E0E0', overflow: 'hidden' },
  noDueCard: { backgroundColor: 'white', borderRadius: 12, padding: 30, marginBottom: 20, alignItems: 'center', borderWidth: 2, borderColor: '#E0E0E0', borderStyle: 'dashed' },
  noDueText: { fontSize: 16, fontWeight: '600', color: '#666', marginBottom: 5 },
  noDueSubtext: { fontSize: 13, color: '#999' },
});